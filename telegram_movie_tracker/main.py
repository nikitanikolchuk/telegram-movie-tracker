import logging
import re
from datetime import date, time

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from tmdbsimple import Movies, TV
from tmdbsimple.find import Find

from telegram_movie_tracker.db.models import User, Movie
from telegram_movie_tracker.settings import env

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

IMAGE_URL_PREFIX='https://image.tmdb.org/t/p/w500'


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
        show_info = Movies(find_info['movie_results'][0]['id']).info()
        if show_info['status'] == 'Released':
            await update.message.reply_text("The movie was already released")
            return
        try:
            await Movie.objects.track_movie(show_info, update.effective_user.id)
        except ValueError:
            await update.message.reply_text(f"You are already tracking {show_info['title']}")
    elif find_info['tv_results'] or find_info['tv_episode_results']:
        if find_info['tv_results']:
            show_info = TV(find_info['tv_results'][0]['id']).info()
        else:
            show_info = TV(find_info['tv_episode_results'][0]['show_id']).info()
        # TODO
        await update.message.reply_text("TV shows are not supported yet")
        return
    else:
        await update.message.reply_text("Invalid link")
        return

    await update.message.reply_text(f"Started tracking {show_info['title']}")


@sync_to_async
def get_movie_releases() -> list[tuple[User, Movie, str]]:
    """
    Get new movie releases as a list of tuples (tracking_user, released_movie, image_url).
    Released shows are deleted.
    """
    releases = []
    for movie in Movie.objects.all():
        if movie.release_date is not None and movie.release_date <= date.today():
            poster_path = Movies(movie.id).info()['poster_path']
            image_url = IMAGE_URL_PREFIX + poster_path
            for user in movie.users.all():
                releases.append((user, movie, image_url))
            movie.delete()
    return releases


async def send_releases(context: ContextTypes.DEFAULT_TYPE):
    """Send info about new releases to users tracking them"""
    for (user, movie, image_url) in await get_movie_releases():
        await context.bot.send_photo(
            chat_id=user.id,
            photo=image_url,
            caption=f"{movie.title} was released"
        )


def main() -> None:
    application = (
        ApplicationBuilder()
        .token(env('BOT_TOKEN'))
        .build()
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('track', track))

    application.job_queue.run_daily(send_releases, time(hour=18, minute=0))
    # TODO: add a job for updating show info

    application.run_polling()


if __name__ == '__main__':
    main()
