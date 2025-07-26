import requests
import os
import logging
import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Order

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def send_order_notification(sender, instance, created, update_fields, **kwargs):
    logger.info(
        f"Signal ishga tushdi: Order ID {instance.order_id}, Created: {created}, Update Fields: {update_fields}")


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
                    logger.info("Xabar muvaffaqiyatli yuborildi")
            except requests.RequestException as e:
                logger.error(
                    f"Telegram xabar yuborishda xato: {e}, Javob: {response.text if 'response' in locals() else 'Yoq'}")
            except IOError as e:
                logger.error(f"Fayl ochishda xato: {e}")
        else:
            logger.warning(f"To'lov cheki fayli mavjud emas: {instance.payment_screenshot.path}")
    else:
        logger.info(
            f"Shart bajarilmadi: created={created}, payment_screenshot={instance.payment_screenshot}, update_fields={update_fields}")
