import django
import environ
from django.conf import settings

env = environ.Env()
env.read_env()


def init_django() -> None:
    """Connect to database and setup Django ORM"""
    if settings.configured:
        return

    settings.configure(
        INSTALLED_APPS=[
            'telegram_movie_tracker.db'
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': env('DB_NAME'),
                'USER': env('DB_USER'),
                'PASSWORD': env('DB_PASSWORD'),
                'HOST': env('DB_HOST'),
                'PORT': env('DB_PORT'),
            }
        }
    )
    django.setup()
