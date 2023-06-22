import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telegram_movie_tracker.settings')

app = Celery(
    'celery_app',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

app.config_from_object(
    'django.conf:settings',
    namespace='CELERY'
)

app.conf.update(
    imports=['telegram_movie_tracker.tasks.tasks']
)
