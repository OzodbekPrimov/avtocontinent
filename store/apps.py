from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'

    def ready(self):
        logger.info("StoreConfig ready metodi ishga tushdi")
        import store.signals