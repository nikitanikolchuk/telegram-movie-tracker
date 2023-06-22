from datetime import datetime

import django
import environ
from celery.schedules import crontab
from django.conf import settings

env = environ.Env()
env.read_env()

INSTALLED_APPS = [
    'telegram_movie_tracker',
    'telegram_movie_tracker.db'
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    }
}

CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BEAT_SCHEDULE = {
    'test_task': {
        'task': 'telegram_movie_tracker.tasks.test_task',
        'schedule': crontab(),
        'args' : {datetime.now()}
    }
}


def init_django() -> None:
    """Connect to database and setup Django ORM"""
    if settings.configured:
        return

    settings.configure(
        INSTALLED_APPS=INSTALLED_APPS,
        DATABASES=DATABASES
    )
    django.setup()
