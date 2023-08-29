from django.db import models

from telegram_movie_tracker.db.managers import MovieManager, TVShowManager
from telegram_movie_tracker.settings import init_django

init_django()


class User(models.Model):
    """Class representing a Telegram user"""

    class Meta:
        db_table = 'user'

    id = models.BigIntegerField(primary_key=True)


class Movie(models.Model):
    """Class representing a movie from IMDB"""

    class Meta:
        db_table = 'movie'

    objects = MovieManager()

    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=256)
    users = models.ManyToManyField(User, related_name='movies', db_table='movie_user')


class TVShow(models.Model):
    """Class representing a TV show from IMDB"""

    class Meta:
        db_table = 'tv_show'

    objects = TVShowManager()

    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=256)
    last_season = models.IntegerField()
    last_episode = models.IntegerField()
    users = models.ManyToManyField(User, related_name='tv_shows', db_table='tv_show_user')
