from datetime import datetime

from asgiref.sync import sync_to_async
from django.db import models


class MovieManager(models.Manager):
    """Manager class for Movie model"""

    def get_or_create_movie(self, movie_info: dict):
        if 'release_date' in movie_info and movie_info['release_date'] != '':
            release_date = datetime.strptime(movie_info['release_date'], '%Y-%m-%d').date()
        else:
            release_date = None
        movie, _ = super().get_queryset().get_or_create(
            id=movie_info['id'],
            title=movie_info['title'],
            release_date=release_date
        )
        return movie

    @sync_to_async
    def track_movie(self, movie_info: dict, user_id: int) -> None:
        movie = self.get_or_create_movie(movie_info)
        if movie.users.filter(id=user_id).exists():
            raise ValueError(f"Already tracking this movie")
        movie.users.add(user_id)


class TVShowManager(models.Manager):
    """Manager class for TVShow model"""

    def get_or_create_tv_show(self, tv_show_info: dict):
        if 'last_episode_to_air' in tv_show_info:
            last_season = tv_show_info['last_episode_to_air']['season_number']
            last_episode = tv_show_info['last_episode_to_air']['episode_number']
        else:
            last_season = 0
            last_episode = 0
        tv_show, _ = super().get_queryset().get_or_create(
            id=tv_show_info['id'],
            title=tv_show_info['name'],
            last_season=last_season,
            last_episode=last_episode
        )
        return tv_show

    @sync_to_async
    def track_tv_show(self, tv_show_info: dict, user_id: int) -> None:
        tv_show = self.get_or_create_tv_show(tv_show_info)
        if tv_show.users.filter(id=user_id).exists():
            raise ValueError(f"Already tracking this TV show")
        tv_show.users.add(user_id)
