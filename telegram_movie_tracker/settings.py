import django
import environ
import tmdbsimple as tmdb
from django.conf import settings

env = environ.Env()
env.read_env()

tmdb.API_KEY = env('API_KEY')

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


def init_django() -> None:
    """Connect to database and setup Django ORM"""
    if settings.configured:
        return

    settings.configure(
        INSTALLED_APPS=INSTALLED_APPS,
        DATABASES=DATABASES
    )
    django.setup()
