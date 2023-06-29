import itertools
import logging
import re
from datetime import time
from typing import Any, Callable, cast, Coroutine

import requests
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from tmdbsimple import Movies, TV
from tmdbsimple.find import Find

from telegram_movie_tracker.db.models import User, Movie, TVShow
from telegram_movie_tracker.settings import env

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

IMAGE_URL_PREFIX = 'https://image.tmdb.org/t/p/w500'


def button_markup(buttons: [str, Callable[..., str]]) -> InlineKeyboardMarkup:
    """Construct keyboard markup from a list of tuples (button_text, callable)"""
    return InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton(text=text, callback_data=callback) for (text, callback) in buttons]
    )


@sync_to_async
def get_show_list(user: User) -> list[Movie | TVShow]:
    """Get a list of all shows tracked by user"""
    return list(itertools.chain(user.movies.all(), user.tv_shows.all()))  # type: ignore


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hello! I'm a bot for tracking releases of new shows. "
        "To get info about commands use /help"
    )
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
        try:
            await Movie.objects.track_movie(movie_info, update.effective_user.id)
        except ValueError as e:
            await update.message.reply_text(str(e))
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
def stop_tracking(show: Movie | TVShow, user: User) -> str:
    """Function to stop tracking a show"""
    show.users.remove(user)
    return f"Stopped tracking {show.title}"


async def stop(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Command to stop tracking a show"""
    user = await sync_to_async(User.objects.get)(pk=update.effective_user.id)  # type: ignore
    shows = await get_show_list(user)
    keyboard = [(s.title, lambda: stop_tracking(s, user)) for s in shows]
    await update.message.reply_text(
        text="Choose the show you want to stop tracking",
        reply_markup=button_markup(keyboard)
    )


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


async def get_shows(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send user a list of tracked movies and tv shows"""
    await update.message.reply_text(await get_tracked_list(update.effective_user.id))


async def get_help(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send info about available commands"""
    await update.message.reply_text(
        "The bot allows you to track releases of new movies and episodes of your TV shows.\n"
        "\n"
        "To add a show send a link to it's page on imdb.com in the format:\n"
        "/track {url}\n"
        "\n"
        "To get a list of your tracked shows use /shows command"
    )


async def button_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a button click by calling the associated function"""
    query = update.callback_query

    await query.answer()

    callback = cast(Callable[..., Coroutine[Any, Any, str]], query.data)
    await query.edit_message_text(await callback())


@sync_to_async
def get_movie_releases() -> list[tuple[User, str, str]]:
    """
    Get new movie releases as a list of tuples (tracking_user, message_text, poster_url).
    Released shows are deleted from the database.
    """
    releases = []
    for movie in Movie.objects.all():
        movie_info = Movies(movie.id).info()
        if 'status' in movie_info and movie_info['status'] == 'Released':
            message_text = f"{movie.title} was released"
            poster_url = ''
            if 'poster_path' in movie_info:
                poster_url = IMAGE_URL_PREFIX + str(movie_info['poster_path'])
            for user in movie.users.all():
                releases.append((user, message_text, poster_url))
            movie.delete()
    return releases


@sync_to_async
def get_tv_show_releases() -> list[tuple[User, str, str]]:
    """
    Get new tv show episode releases as a list of tuples (tracking_user, message_text, poster_url).
    """
    releases = []
    for tv_show in TVShow.objects.all():
        tv_show_info = TV(tv_show.id).info()
        if 'last_episode_to_air' in tv_show_info and tv_show_info['last_episode_to_air'] != '':
            last_episode_info = tv_show_info['last_episode_to_air']
            poster_url = ''
            if last_episode_info['season_number'] > tv_show.last_season:
                tv_show.last_season = last_episode_info['season_number']
                tv_show.last_episode = last_episode_info['episode_number']
                tv_show.save()
                message_text = f"{tv_show.title} Season {tv_show.last_season} was released.\n" \
                               f"Number of already available episodes is {tv_show.last_episode}"
                if 'poster_path' in tv_show_info['seasons'][tv_show.last_season]:
                    poster_url = IMAGE_URL_PREFIX + str(tv_show_info['seasons'][tv_show.last_season]['poster_path'])
            elif last_episode_info['episode_number'] > tv_show.last_episode:
                tv_show.last_episode = last_episode_info['episode_number']
                tv_show.save()
                message_text = f"{tv_show.title} Season {tv_show.last_season} Episode " \
                               f"{tv_show.last_episode} was released"
                if 'still_path' in last_episode_info:
                    poster_url = IMAGE_URL_PREFIX + str(last_episode_info['still_path'])
            else:
                continue
            for user in tv_show.users.all():
                releases.append((user, message_text, poster_url))
    return releases


async def send_releases(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send info about new releases to users tracking them"""
    releases = itertools.chain(await get_movie_releases(), await get_tv_show_releases())
    for (user, message_text, poster_url) in releases:
        if poster_url != '':
            poster = requests.get(poster_url, stream=True).content
            await context.bot.send_photo(
                chat_id=user.id,
                photo=poster,
                caption=message_text
            )
        else:
            await context.bot.send_message(
                chat_id=user.id,
                text=message_text
            )


def main() -> None:
    application = (
        ApplicationBuilder()
        .token(env('BOT_TOKEN'))
        .arbitrary_callback_data(True)
        .build()
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('track', track))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('shows', get_shows))
    application.add_handler(CommandHandler('help', get_help))
    application.add_handler(MessageHandler(
        filters.COMMAND,
        callback=lambda update, _: update.message.reply_text("Unknown command, see /help")
    ))
    application.add_handler(MessageHandler(
        filters.ALL,
        callback=lambda update, _: update.message.reply_text("Not a command, see /help")
    ))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.job_queue.run_daily(send_releases, time(hour=16, minute=0))

    application.run_polling()


if __name__ == '__main__':
    main()
