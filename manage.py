import sys
import django
from django.conf import settings


def init_django() -> None:
    """Connect to database and setup Django ORM"""
    if settings.configured:
        return

    settings.configure(
        INSTALLED_APPS=[
            'db',
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


if __name__ == '__main__':
    from django.core.management import execute_from_command_line

    init_django()
    execute_from_command_line(sys.argv)
