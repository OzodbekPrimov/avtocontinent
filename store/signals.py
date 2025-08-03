import requests
import os
import logging
import json
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.conf import settings
from .models import Order

logger = logging.getLogger(__name__)

# Status o'zgarishini kuzatish uchun
_order_old_status = {}


def send_telegram_message(chat_id, message, reply_markup=None):
    """Telegram orqali xabar yuborish uchun yordamchi funksiya"""
    telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        response = requests.post(telegram_url, data=payload)
        response.raise_for_status()
        logger.info(f"Telegram xabar yuborildi: chat_id={chat_id}")
        return True
    except requests.RequestException as e:
        logger.error(f"Telegram xabar yuborishda xato: {e}")
        return False


def notify_customer_status_change(order_instance, old_status, new_status):
    """Mijozga order status o'zgarishi haqida xabar yuborish"""
    try:
        user_profile = order_instance.user.userprofile
        if not user_profile.telegram_chat_id:
            logger.info(f"Order {order_instance.order_id} uchun mijoz telegram chat ID mavjud emas")
            return
        telegram_chat_id = user_profile.telegram_chat_id
    except Exception as e:
        logger.error(f"User profile topishda xato: {e}")
        return

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

    message = (
        f"{emoji} <b>Buyurtma holati o'zgardi!</b>\n\n"
        f"🆔 Buyurtma raqami: <b>#{order_instance.order_id}</b>\n"
        f"📊 Eski holat: <b>{old_status_name}</b>\n"
        f"📊 Yangi holat: <b>{new_status_name}</b>\n"
        f"💰 Umumiy summa: <b>${order_instance.total_amount_usd}</b>\n"
        f"📅 Sana: <b>{order_instance.created_at.strftime('%d.%m.%Y %H:%M')}</b>"
    )

    # Qo'shimcha xabarlar har bir status uchun
    if new_status == 'confirmed':
        message += "\n\n🎉 Buyurtmangiz tasdiqlandi! Tez orada tayyorlanishni boshlaymiz."
    elif new_status == 'preparing':
        message += "\n\n🔄 Buyurtmangiz tayyorlanmoqda. Sabr qiling!"
    elif new_status == 'shipped':
        message += "\n\n🚚 Buyurtmangiz jo'natildi! Tez orada qo'lingizga yetadi."
    elif new_status == 'delivered':
        message += "\n\n📦 Buyurtmangiz muvaffaqiyatli yetkazildi! Xaridingiz uchun rahmat!"
    elif new_status == 'cancelled':
        message += "\n\n❌ Afsuski, buyurtmangiz bekor qilindi. Savollar uchun bog'laning."

    send_telegram_message(telegram_chat_id, message)


@receiver(pre_save, sender=Order)
def store_old_status(sender, instance, **kwargs):
    """Eski statusni saqlash"""
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            _order_old_status[instance.pk] = old_instance.status
        except Order.DoesNotExist:
            _order_old_status[instance.pk] = None


@receiver(post_save, sender=Order)
def send_order_notification(sender, instance, created, update_fields, **kwargs):
    logger.info(
        f"Signal ishga tushdi: Order ID {instance.order_id}, Created: {created}, Update Fields: {update_fields}")

    # Status o'zgarganligini tekshirish
    if not created and instance.pk in _order_old_status:
        old_status = _order_old_status.get(instance.pk)
        new_status = instance.status

        if old_status and old_status != new_status:
            logger.info(f"Order {instance.order_id} status o'zgardi: {old_status} -> {new_status}")

            # Mijozga xabar yuborish
            notify_customer_status_change(instance, old_status, new_status)

        # Eski statusni o'chirish
        del _order_old_status[instance.pk]

    # Payment screenshot yuklanganda adminga xabar yuborish (eski kod)
    if update_fields and 'payment_screenshot' in update_fields and instance.payment_screenshot:
        if os.path.exists(instance.payment_screenshot.path):
            logger.info(f"To'lov cheki fayli: {instance.payment_screenshot.path}")

            try:
                order_items = instance.items.all()
                items_text = "\n".join(
                    [f"- {item.product.name} x {item.quantity} (${item.total_price_usd})" for item in order_items])
            except AttributeError as e:
                logger.error(f"Mahsulotlar olishda xato: {e}")
                items_text = "Mahsulotlar mavjud emas"

            message = (
                f"🔔 Yangi buyurtma!\n"
                f"Buyurtma ID: {instance.order_id}\n"
                f"Mijoz: {instance.customer_name}\n"
                f"Telefon: {instance.customer_phone}\n"
                f"Manzil: {instance.customer_address}\n"
                f"Umumiy narx (USD): ${instance.total_amount_usd}\n"
                f"Umumiy narx (UZS): {instance.total_amount_uzs} so'm\n"
                f"Status: {instance.get_status_display()}\n"
                f"Mahsulotlar:\n{items_text}\n"
                f"Yaratilgan vaqt: {instance.created_at.strftime('%Y-%m-%d %H:%M')}"
            )

            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ To'lovni tasdiqlash", "callback_data": f"confirm_{instance.order_id}"},
                        {"text": "❌ To'lovni bekor qilish", "callback_data": f"cancel_{instance.order_id}"}
                    ]
                ]
            }

            telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendPhoto"
            try:
                with open(instance.payment_screenshot.path, 'rb') as photo:
                    files = {'photo': photo}
                    payload = {
                        "chat_id": settings.TELEGRAM_ADMIN_CHAT_ID,
                        "caption": message,
                        "parse_mode": "Markdown",
                        "reply_markup": json.dumps(keyboard)
                    }
                    response = requests.post(telegram_url, data=payload, files=files)
                    response.raise_for_status()
                    logger.info("Admin uchun xabar muvaffaqiyatli yuborildi")
            except requests.RequestException as e:
                logger.error(
                    f"Admin uchun telegram xabar yuborishda xato: {e}, Javob: {response.text if 'response' in locals() else 'Yoq'}")
            except IOError as e:
                logger.error(f"Fayl ochishda xato: {e}")
        else:
            logger.warning(f"To'lov cheki fayli mavjud emas: {instance.payment_screenshot.path}")
    else:
        logger.info(
            f"Shart bajarilmadi: created={created}, payment_screenshot={instance.payment_screenshot}, update_fields={update_fields}")