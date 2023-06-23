import datetime
import logging
import re
from datetime import date, time

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from tmdbsimple import Movies, TV
from tmdbsimple.find import Find

from telegram_movie_tracker.db.models import User, Movie, TVShow
from telegram_movie_tracker.settings import env

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

IMAGE_URL_PREFIX = 'https://image.tmdb.org/t/p/w500'


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! I'm a bot for tracking releases of new shows")
    if not await sync_to_async(User.objects.filter(id=update.effective_user.id).exists)():  # type: ignore
        await sync_to_async(User(update.effective_user.id).save)()  # type: ignore


async def track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to add an IMDB show in the format '/track {url}' """
    if len(context.args) != 1:
        await update.message.reply_text("Command is not in the format '/track {url}'")
        return
    match = re.match(r'(https://www\.|www\.)?imdb\.com/title/(?P<id>tt[0-9]+)/.*', context.args[0])
    if not match:
        await update.message.reply_text("Invalid link")
        return

    find_info = Find(match.group('id')).info(external_source='imdb_id')
    if find_info['movie_results']:
        movie_info = Movies(find_info['movie_results'][0]['id']).info()
        show_name = movie_info['title']
        if movie_info['status'] == 'Released':
            await update.message.reply_text("The movie was already released")
            return
        try:
            await Movie.objects.track_movie(movie_info, update.effective_user.id)
        except ValueError:
            await update.message.reply_text(f"You are already tracking {movie_info['title']}")
            return
    elif find_info['tv_results'] or find_info['tv_episode_results']:
        if find_info['tv_results']:
            tv_show_info = TV(find_info['tv_results'][0]['id']).info()
        else:
            tv_show_info = TV(find_info['tv_episode_results'][0]['show_id']).info()
        show_name = tv_show_info['name']
        try:
            await TVShow.objects.track_tv_show(tv_show_info, update.effective_user.id)
        except ValueError:
            await update.message.reply_text(f"You are already tracking {tv_show_info['name']}")
            return
    else:
        await update.message.reply_text("Invalid link")
        return

    await update.message.reply_text(f"Started tracking {show_name}")


@sync_to_async
def get_tracked_list(user_id: int) -> str:
    """Get a list of movies and TV shows for this user as a str"""
    message_text = "Movies:\n"
    user = User.objects.get(pk=user_id)  # type: ignore
    for movie in user.movies.all():
        message_text += f"- {movie.title}\n"
    message_text += "TV shows:\n"
    for tv_show in user.tv_shows.all():
        message_text += f"- {tv_show.title}\n"
    return message_text


async def shows(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send user a list of tracked movies and tv shows"""
    await update.message.reply_text(await get_tracked_list(update.effective_user.id))


@sync_to_async
def get_movie_releases() -> list[tuple[User, Movie, str]]:
    """
    Get new movie releases as a list of tuples (tracking_user, released_movie, image_url).
    Released shows are deleted from the database.
    """
    releases = []
    for movie in Movie.objects.all():
        movie_info = Movies(movie.id).info()
        if 'release_date' in movie_info and movie_info['release_date'] != '':
            movie.release_date = datetime.datetime.strptime(movie_info['release_date'], '%Y-%m-%d').date()
            movie.save()
        if movie.release_date is not None and movie.release_date <= date.today():
            image_url = IMAGE_URL_PREFIX
            if 'poster_path' in movie_info:
                image_url += str(movie_info['poster_path'])
            for user in movie.users.all():
                releases.append((user, movie, image_url))
            movie.delete()
    return releases


@sync_to_async
def get_tv_show_releases() -> list[tuple[User, str, str]]:
    """
    Get new tv show episode releases as a list of tuples (tracking_user, message_text, image_url).
    """
    releases = []
    for tv_show in TVShow.objects.all():
        tv_show_info = TV(tv_show.id).info()
        if 'last_episode_to_air' in tv_show_info and tv_show_info['last_episode_to_air'] != '':
            last_episode_info = tv_show_info['last_episode_to_air']
            image_url = IMAGE_URL_PREFIX
            if last_episode_info['season_number'] > tv_show.last_season:
                tv_show.last_season = last_episode_info['season_number']
                tv_show.last_episode = last_episode_info['episode_number']
                tv_show.save()
                message_text = f"{tv_show.title} Season {tv_show.last_season} was released.\n" \
                               f"Number of already available episodes is {tv_show.last_episode}"
                if 'poster_path' in tv_show_info['seasons'][tv_show.last_season]:
                    image_url += str(tv_show_info['seasons'][tv_show.last_season]['poster_path'])
            elif last_episode_info['episode_number'] > tv_show.last_episode:
                tv_show.last_episode = last_episode_info['episode_number']
                tv_show.save()
                message_text = f"{tv_show.title} Season {tv_show.last_season} episode " \
                               f"{tv_show.last_episode} was released"
                if 'poster_path' in last_episode_info['still_path']:
                    image_url += str(last_episode_info['still_path'])
            else:
                continue
            for user in tv_show.users.all():
                releases.append((user, message_text, image_url))
    return releases


async def send_releases(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send info about new releases to users tracking them"""
    # TODO: get rid of code duplication
    for (user, movie, image_url) in await get_movie_releases():
        try:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=image_url,
                caption=f"{movie.title} was released"
            )
        except BadRequest:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"{movie.title} was released"
            )

    for (user, message_text, image_url) in await get_tv_show_releases():
        try:
            await context.bot.send_photo(
                chat_id=user.id,
                photo=image_url,
                caption=message_text
            )
        except BadRequest:
            await context.bot.send_message(
                chat_id=user.id,
                text=message_text
            )


def main() -> None:
    application = (
        ApplicationBuilder()
        .token(env('BOT_TOKEN'))
        .build()
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('track', track))
    application.add_handler(CommandHandler('shows', shows))

    application.job_queue.run_daily(send_releases, time(hour=18, minute=0))

    application.run_polling()


if __name__ == '__main__':
    main()
