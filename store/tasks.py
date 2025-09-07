import time

from celery import shared_task
import requests
import os
import logging
import json
from django.conf import settings
from django.utils import timezone
import pytz
from .models import Order, PaymentSettings

logger = logging.getLogger(__name__)


def get_admin_chat_id():
    settings_obj = PaymentSettings.objects.first()
    return settings_obj.admin_chat_id if settings_obj else None


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_telegram_message_task(self, chat_id, message, reply_markup=None):
    """Telegram orqali xabar yuborish uchun asenkron vazifa"""
    telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        response = requests.post(telegram_url, data=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"Telegram xabar yuborildi: chat_id={chat_id}")
        return {"success": True, "chat_id": chat_id}
    except requests.RequestException as e:
        logger.error(f"Telegram xabar yuborishda xato: {e}")
        # Celery avtomatik retry qiladi
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_telegram_photo_task(self, chat_id, photo_path, caption, reply_markup=None):
    """Telegram orqali rasm yuborish uchun asenkron vazifa"""
    telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendPhoto"

    if not os.path.exists(photo_path):
        logger.error(f"Fayl mavjud emas: {photo_path}")
        return {"success": False, "error": "File not found"}

    try:
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            payload = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "Markdown"
            }

            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)

            response = requests.post(telegram_url, data=payload, files=files, timeout=30)
            response.raise_for_status()
            logger.info(f"Telegram rasm yuborildi: chat_id={chat_id}")
            return {"success": True, "chat_id": chat_id}
    except requests.RequestException as e:
        logger.error(f"Telegram rasm yuborishda xato: {e}")
        raise self.retry(exc=e, countdown=60)
    except IOError as e:
        logger.error(f"Fayl ochishda xato: {e}")
        return {"success": False, "error": str(e)}


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def notify_customer_status_change_task(self, order_id, old_status, new_status):
    """Mijozga order status o'zgarishi haqida asenkron xabar yuborish"""
    try:
        order_instance = Order.objects.get(pk=order_id)

        try:
            user_profile = order_instance.user.userprofile
            if not user_profile.telegram_chat_id:
                logger.info(f"Order {order_instance.order_id} uchun mijoz telegram chat ID mavjud emas")
                return {"success": False, "error": "No telegram chat ID"}
            telegram_chat_id = user_profile.telegram_chat_id
        except Exception as e:
            logger.error(f"User profile topishda xato: {e}")
            return {"success": False, "error": str(e)}

        # Status o'zbekcha nomi
        status_names = {
            'pending': 'Kutilmoqda',
            'confirmed': 'Tasdiqlandi',
            'preparing': 'Tayyorlanmoqda',
            'shipped': 'Jo\'natildi',
            'delivered': 'Yetkazildi',
            'cancelled': 'Bekor qilindi'
        }

        # Status emojilar
        status_emojis = {
            'pending': '⏳',
            'confirmed': '✅',
            'preparing': '🔄',
            'shipped': '🚚',
            'delivered': '📦',
            'cancelled': '❌'
        }

        old_status_name = status_names.get(old_status, old_status)
        new_status_name = status_names.get(new_status, new_status)
        emoji = status_emojis.get(new_status, '📋')

        # Convert to Tashkent timezone
        tashkent_tz = pytz.timezone('Asia/Tashkent')
        created_at_tashkent = order_instance.created_at.astimezone(tashkent_tz)
        updated_at_tashkent = timezone.now().astimezone(tashkent_tz)
        
        message = (
            f"{emoji} <b>Buyurtma holati o'zgardi!</b>\n\n"
            f"🆔 Buyurtma raqami: <b>#{order_instance.order_id}</b>\n"
            f"📊 Eski holat: <b>{old_status_name}</b>\n"
            f"📊 Yangi holat: <b>{new_status_name}</b>\n"
            f"💰 Umumiy summa: <b>{order_instance.total_amount_uzs}uzs</b>\n"
            f"📅 Yaratilgan vaqt: <b>{created_at_tashkent.strftime('%d.%m.%Y %H:%M')}</b>\n"
            f"🕒 O'zgartirilgan vaqt: <b>{updated_at_tashkent.strftime('%d.%m.%Y %H:%M')}</b>"
        )

        # Qo'shimcha xabarlar har bir status uchun
        if new_status == 'confirmed':
            message += "\n\n🎉 Buyurtmangiz tasdiqlandi! Tez orada yuboramiz"
        elif new_status == 'preparing':
            message += "\n\n🔄 Buyurtmangiz tayyorlanmoqda. Sabr qiling!"
        elif new_status == 'shipped':
            message += "\n\n🚚 Buyurtmangiz jo'natildi! Tez orada qo'lingizga yetadi."
        elif new_status == 'delivered':
            message += "\n\n📦 Buyurtmangiz muvaffaqiyatli yetkazildi! Tanlagan filialingizdan borib olishingiz mumkin. Xaridingiz uchun rahmat!"
        elif new_status == 'cancelled':
            message += "\n\n❌ Afsuski, buyurtmangiz bekor qilindi. Savollar uchun bog'laning."

        # Telegram xabar yuborish vazifasini chaqirish
        return send_telegram_message_task.delay(telegram_chat_id, message)

    except Order.DoesNotExist:
        logger.error(f"Order topilmadi: {order_id}")
        return {"success": False, "error": "Order not found"}
    except Exception as e:
        logger.error(f"Status o'zgarishi xabarini yuborishda xato: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_admin_payment_notification_task(self, order_id):
    time.sleep(5)
    """Adminga to'lov cheki haqida asenkron xabar yuborish"""
    try:
        order_instance = Order.objects.get(pk=order_id)

        if not order_instance.payment_screenshot:
            logger.error(f"Order {order_id} uchun payment screenshot mavjud emas")
            return {"success": False, "error": "No payment screenshot"}

        if not os.path.exists(order_instance.payment_screenshot.path):
            logger.error(f"To'lov cheki fayli mavjud emas: {order_instance.payment_screenshot.path}")
            return {"success": False, "error": "File not found"}

        try:
            order_items = order_instance.items.all()
            items_text = "\n".join(
                [f"- {item.product.name} x {item.quantity} (${item.total_price_usd})" for item in order_items])
        except AttributeError as e:
            logger.error(f"Mahsulotlar olishda xato: {e}")
            items_text = "Mahsulotlar mavjud emas"

        # Get delivery branch information (region and branch name only)
        delivery_info = "Filial tanlanmagan"
        if order_instance.delivery_branch_id:
            try:
                branch_info = order_instance.delivery_branch_info
                if branch_info:
                    region = branch_info.get('region', 'Nomalum viloyat')
                    branch_name = branch_info.get('name', 'Nomalum filial')
                    delivery_info = f"{region} - {branch_name}"
                else:
                    delivery_info = f"Filial ID: {order_instance.delivery_branch_id}"
            except Exception as e:
                logger.error(f"Filial ma'lumotlarini olishda xato: {e}")
                delivery_info = f"Filial ID: {order_instance.delivery_branch_id}"
        
        # Convert to Tashkent timezone
        tashkent_tz = pytz.timezone('Asia/Tashkent')
        created_at_tashkent = order_instance.created_at.astimezone(tashkent_tz)
        
        message = (
            f"🔔 Yangi buyurtma!\n"
            f"🆔 Buyurtma ID: {order_instance.order_id}\n"
            f"👤 Mijoz: {order_instance.customer_name}\n"
            f"📱 Telefon: {order_instance.customer_phone}\n"
            f"🏪 Yetkazib berish: {delivery_info}\n"
            f"💰 Umumiy narx (USD): ${order_instance.total_amount_usd}\n"
            f"💰 Umumiy narx (UZS): {order_instance.total_amount_uzs} so'm\n"
            f"💱 Kurs: {order_instance.exchange_rate_used}\n"
            f"📊 Status: {order_instance.get_status_display()}\n"
            f"📦 Mahsulotlar:\n{items_text}\n"
            f"📅 Yaratilgan vaqt: {created_at_tashkent.strftime('%d.%m.%Y %H:%M')}"
        )
        
        # Add additional instructions if they exist
        if order_instance.additional_instructions:
            message += f"\n📝 Qo'shimcha ko'rsatmalar: {order_instance.additional_instructions}"

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ To'lovni tasdiqlash", "callback_data": f"confirm_{order_instance.order_id}"},
                    {"text": "❌ To'lovni bekor qilish", "callback_data": f"cancel_{order_instance.order_id}"}
                ]
            ]
        }
        admin_id = get_admin_chat_id()
        # Telegram rasm yuborish vazifasini chaqirish
        return send_telegram_photo_task.delay(
            admin_id,
            order_instance.payment_screenshot.path,
            message,
            keyboard
        )

    except Order.DoesNotExist:
        logger.error(f"Order topilmadi: {order_id}")
        return {"success": False, "error": "Order not found"}
    except Exception as e:
        logger.error(f"Admin xabarini yuborishda xato: {e}")
        raise self.retry(exc=e, countdown=60)