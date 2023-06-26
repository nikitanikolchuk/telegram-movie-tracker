from asgiref.sync import sync_to_async
from django.test import TestCase

from telegram_movie_tracker.db.models import User, Movie, TVShow


class MovieTestCase(TestCase):
    def test_update_or_create_movie(self) -> None:
        movie_info1 = {'id': 1, 'title': 'title1'}
        movie1 = Movie.objects.update_or_create_movie(movie_info1)
        self.assertEqual(1, movie1.id)
        self.assertEqual('title1', movie1.title)

        movie2 = Movie.objects.update_or_create_movie(movie_info1)
        self.assertEqual(movie2, movie1)

        movie_info2 = {'id': 1, 'title': 'title2'}
        movie3 = Movie.objects.update_or_create_movie(movie_info2)
        self.assertEqual(movie3, movie1)
        self.assertEqual(1, movie3.id)
        self.assertEqual('title2', movie3.title)

    async def test_track_movie(self) -> None:
        user = await sync_to_async(User.objects.create)(id=1)  # type: ignore

        movie_info1 = {'id': 1, 'title': 'title1', 'status': None}
        await Movie.objects.track_movie(movie_info1, user.id)
        self.assertEqual(1, await sync_to_async(user.movies.all().__len__)())
        movie = await sync_to_async(user.movies.first)()
        self.assertEqual(1, movie.id)
        self.assertEqual('title1', movie.title)

        movie_info2 = {'id': 2, 'title': 'title2', 'status': 'Released'}
        with self.assertRaises(ValueError):
            await Movie.objects.track_movie(movie_info2, user.id)

        with self.assertRaises(ValueError):
            await Movie.objects.track_movie(movie_info1, user.id)


class TVShowTestCase(TestCase):
    def test_get_or_create_tv_show(self):
        tv_show_info1 = {'id': 1, 'name': 'title1', 'last_episode_to_air': None}
        tv_show1 = TVShow.objects.get_or_create_tv_show(tv_show_info1)
        self.assertEqual(1, tv_show1.id)
        self.assertEqual('title1', tv_show1.title)
        self.assertEqual(0, tv_show1.last_season)
        self.assertEqual(0, tv_show1.last_episode)

        tv_show_info2 = {
            'id': 1,
            'name': 'title1',
            'last_episode_to_air': {'season_number': 1, 'episode_number': 1}
        }
        tv_show2 = TVShow.objects.get_or_create_tv_show(tv_show_info2)
        self.assertEqual(tv_show2, tv_show1)
        self.assertEqual('title1', tv_show1.title)
        self.assertEqual(0, tv_show1.last_season)
        self.assertEqual(0, tv_show1.last_episode)

        tv_show_info3 = {
            'id': 2,
            'name': 'title2',
            'last_episode_to_air': {'season_number': 1, 'episode_number': 1}
        }
        tv_show3 = TVShow.objects.get_or_create_tv_show(tv_show_info3)
        self.assertEqual(2, tv_show3.id)
        self.assertEqual('title2', tv_show3.title)
        self.assertEqual(1, tv_show3.last_season)
        self.assertEqual(1, tv_show3.last_episode)

    async def test_track_tv_show(self):
        user = await sync_to_async(User.objects.create)(id=1)  # type: ignore

        tv_show_info1 = {'id': 1, 'name': 'title1', 'last_episode_to_air': None}
        await TVShow.objects.track_tv_show(tv_show_info1, user.id)
        self.assertEqual(1, await sync_to_async(user.tv_shows.all().__len__)())
        tv_show = await sync_to_async(user.tv_shows.first)()
        self.assertEqual(1, tv_show.id)
        self.assertEqual('title1', tv_show.title)
        self.assertEqual(0, tv_show.last_season)
        self.assertEqual(0, tv_show.last_episode)

        with self.assertRaises(ValueError):
            await TVShow.objects.track_tv_show(tv_show_info1, user.id)
