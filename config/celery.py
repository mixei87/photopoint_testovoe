import os
from celery import Celery
from django.conf import settings

# Устанавливаем переменную окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Импортируем Django settings для доступа к переменным окружения
import django
django.setup()

# Создаем экземпляр приложения Celery
app = Celery('config')

# Загружаем настройки из настроек Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Получаем URL брокера и бэкенда из настроек Django
broker_url = getattr(settings, 'CELERY_BROKER_URL', None)
result_backend = getattr(settings, 'CELERY_RESULT_BACKEND', None)

if not broker_url or not result_backend:
    raise ValueError(
        "CELERY_BROKER_URL and CELERY_RESULT_BACKEND must be set in Django settings"
    )

# Основные настройки Celery
app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
)

# Устанавливаем опции брокера
app.conf.broker_transport_options = getattr(settings, 'CELERY_BROKER_TRANSPORT_OPTIONS', {})

# Автоматически находим и регистрируем задачи во всех приложениях
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
