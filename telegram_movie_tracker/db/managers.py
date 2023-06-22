from asgiref.sync import sync_to_async
from django.db import models

from telegram_movie_tracker.api.models import Title


class ShowManager(models.Manager):
    """Manager class for Show model"""

    def get_or_create_show(self, title: Title):
        show, _ = super().get_queryset().get_or_create(
            id=title.id,
            name=title.name,
            is_series=title.is_series,
            release_date=title.release_date
        )
        return show

    @sync_to_async
    def track_show(self, title: Title, user_id: int) -> None:
        show = self.get_or_create_show(title)
        if show.users.filter(id=user_id).exists():
            raise ValueError(f"Already tracking this show for this user")
        show.users.add(user_id)
