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
                'NAME': 'postgres',
                'USER': 'postgres',
                'PASSWORD': 'postgres',
                'HOST': '127.0.0.1',
                'PORT': '5432',
            }
        }
    )
    django.setup()
