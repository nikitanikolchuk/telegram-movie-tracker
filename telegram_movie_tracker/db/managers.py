from asgiref.sync import sync_to_async
from django.db import models


class MovieManager(models.Manager):
    """Manager class for Movie model"""

    def get_or_create_movie(self, movie_info: dict):
        if movie_info['release_date'] != '':
            release_date = movie_info['release_date']
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
