import os
from celery import Celery

# Django settings modulini o'rnatish
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('config')

# Django settings dan konfiguratsiyani yuklash
app.config_from_object('django.conf:settings', namespace='CELERY')

# Barcha Django applardan vazifalarni avtomatik topish
app.autodiscover_tasks()

# Celery sozlamalari
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Tashkent',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 daqiqa
    task_soft_time_limit=25 * 60,  # 25 daqiqa
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_compression='gzip',
    result_compression='gzip',
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')