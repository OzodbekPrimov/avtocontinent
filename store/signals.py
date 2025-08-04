import logging
import time

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order
from .tasks import notify_customer_status_change_task, send_admin_payment_notification_task

logger = logging.getLogger(__name__)

# Status o'zgarishini kuzatish uchun
_order_old_status = {}


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

            # Mijozga asenkron xabar yuborish
            try:
                task_result = notify_customer_status_change_task.delay(instance.pk, old_status, new_status)
                logger.info(f"Status o'zgarishi vazifasi yaratildi: {task_result.id}")
            except Exception as e:
                logger.error(f"Status o'zgarishi vazifasini yaratishda xato: {e}")

        # Eski statusni o'chirish
        del _order_old_status[instance.pk]

    # Payment screenshot yuklanganda adminga asenkron xabar yuborish
    if update_fields and 'payment_screenshot' in update_fields and instance.payment_screenshot:
        logger.info(f"To'lov cheki yuklandi: {instance.payment_screenshot.path}")

        try:
            task_result = send_admin_payment_notification_task.delay(instance.pk)
            logger.info(f"Admin xabari vazifasi yaratildi: {task_result.id}")
        except Exception as e:
            logger.error(f"Admin xabari vazifasini yaratishda xato: {e}")
    else:
        logger.info(
            f"Shart bajarilmadi: created={created}, payment_screenshot={instance.payment_screenshot}, update_fields={update_fields}")