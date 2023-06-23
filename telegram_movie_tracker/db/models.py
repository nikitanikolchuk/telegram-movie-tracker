from django.db import models

from telegram_movie_tracker.db.managers import MovieManager
from telegram_movie_tracker.settings import init_django

init_django()


class User(models.Model):
    """Class representing a Telegram user"""

    class Meta:
        db_table = 'user'

    id = models.IntegerField(primary_key=True)


class Movie(models.Model):
    """Class representing a movie from IMDB"""

    class Meta:
        db_table = 'movie'

    objects = MovieManager()

    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=256)
    release_date = models.DateField(blank=True, null=True)
    users = models.ManyToManyField(User, related_name='movies', db_table='movie_user')

# TODO: add TV_show class
