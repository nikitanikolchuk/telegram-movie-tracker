import os
from datetime import date
import requests
from api.models import Title

HEADERS = {
    'X-RapidAPI-Key': os.environ['API_KEY'],
    'X-RapidAPI-Host': 'moviesdatabase.p.rapidapi.com'
}


def get_title(imdb_id: str) -> Title:
    url = f'https://moviesdatabase.p.rapidapi.com/titles/{imdb_id}'
    response = requests.get(url=url, headers=HEADERS).json()['results']
    if response is None:
        raise ValueError("Invalid link")

    release_date = None
    if response['releaseDate'] is not None:
        release_date = date(
            year=response['releaseDate']['year'],
            month=response['releaseDate']['month'],
            day=response['releaseDate']['day']
        )

    return Title(
        imdb_id=imdb_id,
        image_url=response['primaryImage']['url'],
        title_type=response['titleType']['id'],
        is_series=response['titleType']['isSeries'],
        is_episode=response['titleType']['isEpisode'],
        name=response['titleText']['text'],
        release_date=release_date
    )
