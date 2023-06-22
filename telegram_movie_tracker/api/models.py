from datetime import date


class Title:
    """Class representing an IMDB title (e.g. movie, series, episode)"""

    def __init__(
            self,
            imdb_id: str,
            image_url: str,
            title_type: str,
            is_series: bool,
            is_episode: bool,
            name: str,
            release_date: date | None
    ) -> None:
        self.id = imdb_id
        self.image_url = image_url
        self.type = title_type
        self.is_series = is_series
        self.is_episode = is_episode
        self.name = name
        self.release_date = release_date
