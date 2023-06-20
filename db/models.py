import re
from typing import Final
from django.db import models
from manage import init_django

init_django()


class Title(models.Model):
    """Class representing an IMDB title (e.g. movie or series)"""
    class Meta:
        db_table = 'title'

    id = models.IntegerField(primary_key=True, db_column='id_title')
    title_type = models.CharField(max_length=256)
    title_text = models.CharField(max_length=256)

    IMDB_ID_LENGTH: Final[int] = 7

    # TODO: remove default parameters
    @classmethod
    def create(cls, imdb_id: str, title_type: str = "", title_text: str = ""):
        if not re.match(r"^tt[0-9]{7}$", imdb_id):
            raise ValueError(f"IMDB id '{imdb_id}' has incorrect format")
        title = cls(id=int(imdb_id[2:]), title_type=title_type, title_text=title_text)
        return title

    def get_imdb_id(self) -> str:
        return f'tt{str(self.id).zfill(Title.IMDB_ID_LENGTH)}'
