from typing_extensions import Self
from django.db import models
from manage import init_django
from api.models import Title

init_django()


class Show(models.Model):
    """Class representing an IMDB show (e.g. movie or series)"""
    class Meta:
        db_table = 'show'

    id = models.CharField(max_length=256, primary_key=True, db_column='id_show')
    name = models.CharField(max_length=256)
    is_series = models.BooleanField()
    release_date = models.DateField(blank=True, null=True)

    @classmethod
    def create(cls, title: Title) -> Self:
        return cls(
            id=title.id,
            name=title.name,
            is_series=title.is_series,
            release_date=title.release_date
        )
