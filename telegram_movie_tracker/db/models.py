from django.db import models

from settings import init_django
from telegram_movie_tracker.db.managers import ShowManager

init_django()


class User(models.Model):
    """Class representing a Telegram user"""

    class Meta:
        db_table = 'user'

    id = models.IntegerField(primary_key=True)


class Show(models.Model):
    """Class representing an IMDB show (e.g. movie or series)"""

    class Meta:
        db_table = 'show'

    objects = ShowManager()

    id = models.CharField(max_length=256, primary_key=True)
    name = models.CharField(max_length=256)
    is_series = models.BooleanField()
    release_date = models.DateField(blank=True, null=True)
    users = models.ManyToManyField(User, related_name='shows', db_table='show_user')
