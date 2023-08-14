import itertools
import json
import logging
import re
import traceback
from dataclasses import dataclass
from datetime import time
from enum import Enum, auto
from typing import Any

import requests
from asgiref.sync import sync_to_async
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, \
    CallbackQueryHandler, ConversationHandler
from tmdbsimple import Movies, TV
from tmdbsimple.find import Find
from tmdbsimple.search import Search

from telegram_movie_tracker.db.models import User, Movie, TVShow
from telegram_movie_tracker.settings import env

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

IMAGE_URL_PREFIX = 'https://image.tmdb.org/t/p/w500'
CHARACTER_LIMIT = 4096


class TrackState(Enum):
    """Enum for /track conversation handler states"""
    INIT_CHOICE = auto()
    MOVIE = auto()
    MOVIE_CHOICE = auto()
    TV_SHOW = auto()
    TV_SHOW_CHOICE = auto()
    LINK = auto()


@dataclass
class Release:
    """Dataclass for a release of a new show or episode"""
    user: User
    caption: str
    image_url: str


def button_markup(buttons: [str, Any]) -> InlineKeyboardMarkup:
    """Construct keyboard markup from a list of tuples (button_text, callback_data)"""
    return InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton(text=text, callback_data=data) for (text, data) in buttons]
    )


@sync_to_async
def get_show_list(user: User) -> list[Movie | TVShow]:
    """Get a list of all shows tracked by user"""
    return list(itertools.chain(user.movies.all(), user.tv_shows.all()))  # type: ignore


async def start_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hello! I'm a bot for tracking releases of new shows. "
        "To get info about commands use /help"
    )
    if not await sync_to_async(User.objects.filter(id=update.effective_user.id).exists)():  # type: ignore
        await sync_to_async(User(update.effective_user.id).save)()  # type: ignore


async def button_notify_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Click a button or use /cancel")


async def invalid_answer_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Invalid answer, try again or use /cancel")


async def cancel_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Canceled command")
    return ConversationHandler.END


async def track_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> TrackState:
    """Entrypoint for /track command"""
    buttons = [
        ("Search Movie", "movie"),
        ("Search TV Show", "tv_show"),
        ("Send link", "link")
    ]
    await update.message.reply_text(
        text="Choose a show:",
        reply_markup=button_markup(buttons)
    )
    return TrackState.INIT_CHOICE


async def track_init_choice(update: Update, _: ContextTypes.DEFAULT_TYPE) -> TrackState:
    """Handle /track choice"""
    await update.callback_query.answer()
    choice = update.callback_query.data
    if choice == 'movie':
        message_text, state = "Send movie title", TrackState.MOVIE
    elif choice == 'tv_show':
        message_text, state = "Send TV show title", TrackState.TV_SHOW
    else:  # choice == 'link'
        message_text, state = "Send link from imdb.com to the show", TrackState.LINK

    await update.callback_query.message.reply_text(message_text)
    await update.callback_query.message.delete()
    return state


async def track_movie(update: Update, _: ContextTypes.DEFAULT_TYPE) -> TrackState:
    """Send list of movies with given message as a search prompt"""
    results = Search().movie(query=update.message.text)['results']
    if not results:
        await update.message.reply_text("No movies found, try again")
        return TrackState.MOVIE
    buttons = [(f"{m['title']} ({m['release_date'][:4]})", m['id']) for m in results]
    await update.message.reply_text(
        text="Choose a movie:",
        reply_markup=button_markup(buttons)
    )
    return TrackState.MOVIE_CHOICE


async def track_movie_choice(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /track movie choice"""
    await update.callback_query.answer()
    movie_id = update.callback_query.data
    movie_info = Movies(movie_id).info()
    try:
        await Movie.objects.track_movie(movie_info, update.effective_user.id)
    except ValueError as e:
        await update.callback_query.message.reply_text(str(e))
        await update.callback_query.message.delete()
        return ConversationHandler.END

    await update.callback_query.message.reply_text(f"Started tracking {movie_info['title']}")
    await update.callback_query.message.delete()
    return ConversationHandler.END


async def track_tv_show(update: Update, _: ContextTypes.DEFAULT_TYPE) -> TrackState:
    """Send list of TV shows with given message as a search prompt"""
    results = Search().tv(query=update.message.text)['results']
    if not results:
        await update.message.reply_text("No TV shows found, try again")
        return TrackState.TV_SHOW
    # TODO: check if null first_air_date
    buttons = [(f"{t['name']} ({t['first_air_date'][:4]})", t['id']) for t in results]
    await update.message.reply_text(
        text="Choose a TV show:",
        reply_markup=button_markup(buttons)
    )
    return TrackState.TV_SHOW_CHOICE


async def track_tv_show_choice(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle TV show /track choice"""
    await update.callback_query.answer()
    tv_show_id = update.callback_query.data
    tv_show_info = TV(tv_show_id).info()
    try:
        await TVShow.objects.track_tv_show(tv_show_info, update.effective_user.id)
    except ValueError as e:
        await update.callback_query.message.reply_text(str(e))
        await update.callback_query.message.delete()
        return ConversationHandler.END

    await update.callback_query.message.reply_text(f"Started tracking {tv_show_info['name']}")
    await update.callback_query.message.delete()
    return ConversationHandler.END


async def track_link(update: Update, _: ContextTypes.DEFAULT_TYPE) -> TrackState | int:
    """Handle /track link"""
    match = re.match(r'(https://www\.|www\.)?imdb\.com/title/(?P<id>tt[0-9]+)/.*', update.message.text)
    if not match:
        await update.message.reply_text("Invalid link")
        return TrackState.LINK

    find_info = Find(match.group('id')).info(external_source='imdb_id')
    if find_info['movie_results']:
        movie_info = Movies(find_info['movie_results'][0]['id']).info()
        show_name = movie_info['title']
        try:
            await Movie.objects.track_movie(movie_info, update.effective_user.id)
        except ValueError as e:
            await update.message.reply_text(str(e))
            return ConversationHandler.END
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
            return ConversationHandler.END
    else:
        await update.message.reply_text("Invalid link")
        return TrackState.LINK

    await update.message.reply_text(f"Started tracking {show_name}")
    return ConversationHandler.END


async def stop_start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Command to stop tracking a show"""
    user = await sync_to_async(User.objects.get)(pk=update.effective_user.id)  # type: ignore
    shows = await get_show_list(user)
    keyboard = [(s.title, s) for s in shows]
    await update.message.reply_text(
        text="Choose the show you want to stop tracking:",
        reply_markup=button_markup(keyboard)
    )
    return 0


async def stop_choice(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /stop show choice"""
    query = update.callback_query
    await query.answer()
    show: Movie | TVShow = query.data  # type: ignore
    user = await sync_to_async(User.objects.get)(pk=update.effective_user.id)  # type: ignore
    await sync_to_async(show.users.remove)(user)
    await query.edit_message_text(f"Stopped tracking {show.title}")
    return ConversationHandler.END


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


async def shows_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send user a list of tracked movies and tv shows"""
    await update.message.reply_text(await get_tracked_list(update.effective_user.id))


async def help_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send info about available commands"""
    await update.message.reply_text(
        "The bot allows you to track releases of new movies and episodes of your TV shows.\n"
        "\n"
        "To add a show send a link to it's page on imdb.com in the format:\n"
        "/track {url}\n"
        "\n"
        "To get a list of your tracked shows use /shows command"
    )


@sync_to_async
def get_movie_releases() -> list[Release]:
    """Get new movie releases. Released movies are deleted from the database."""
    releases: list[Release] = []
    for movie in Movie.objects.all():
        movie_info = Movies(movie.id).info()
        if 'status' in movie_info and movie_info['status'] == 'Released':
            caption = f"{movie.title} was released"
            poster_url = ''
            if 'poster_path' in movie_info:
                poster_url = IMAGE_URL_PREFIX + str(movie_info['poster_path'])
            for user in movie.users.all():
                releases.append(Release(user, caption, poster_url))
            movie.delete()
    return releases


@sync_to_async
def get_tv_show_releases() -> list[Release]:
    """Get new tv show episode releases"""
    releases: list[Release] = []
    for tv_show in TVShow.objects.all():
        tv_show_info = TV(tv_show.id).info()
        if 'last_episode_to_air' in tv_show_info and tv_show_info['last_episode_to_air'] != '':
            last_episode_info = tv_show_info['last_episode_to_air']
            image_url = ''
            if last_episode_info['season_number'] > tv_show.last_season:
                tv_show.last_season = last_episode_info['season_number']
                tv_show.last_episode = last_episode_info['episode_number']
                tv_show.save()
                caption = f"{tv_show.title} Season {tv_show.last_season} was released.\n" \
                          f"Number of already available episodes is {tv_show.last_episode}"
                if 'poster_path' in tv_show_info['seasons'][tv_show.last_season]:
                    image_url = IMAGE_URL_PREFIX + str(tv_show_info['seasons'][tv_show.last_season]['poster_path'])
            elif last_episode_info['episode_number'] > tv_show.last_episode:
                tv_show.last_episode = last_episode_info['episode_number']
                tv_show.save()
                caption = f"{tv_show.title} Season {tv_show.last_season} Episode " \
                          f"{tv_show.last_episode} was released"
                if 'still_path' in last_episode_info:
                    image_url = IMAGE_URL_PREFIX + str(last_episode_info['still_path'])
            else:
                continue
            for user in tv_show.users.all():
                releases.append(Release(user, caption, image_url))
    return releases


async def send_releases(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send info about new releases to users tracking them"""
    for release in itertools.chain(await get_movie_releases(), await get_tv_show_releases()):
        if release.image_url != '':
            image = requests.get(release.image_url, stream=True).content
            await context.bot.send_photo(
                chat_id=release.user.id,
                photo=image,
                caption=release.caption
            )
        else:
            await context.bot.send_message(
                chat_id=release.user.id,
                text=release.caption
            )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to the dev chat"""
    logging.error("Exception while handling an update:", exc_info=context.error)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    try:
        update_str = json.dumps(update_str, indent=2, ensure_ascii=False)
    except TypeError:
        pass

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    message = (
        f"An exception was raised while handling an update\n"
        f"update = {update_str}\n"
        f"\n"
        f"context.chat_data = {context.chat_data}\n"
        f"\n"
        f"context.user_data = {context.user_data}\n"
        f"\n"
        f"{tb_string}"
    )

    for msg in range(0, len(message), CHARACTER_LIMIT):
        await context.bot.send_message(
            chat_id=env('DEV_CHAT_ID'), text=message[msg:msg + CHARACTER_LIMIT]
        )


def main() -> None:
    application = (
        ApplicationBuilder()
        .token(env('BOT_TOKEN'))
        .arbitrary_callback_data(True)
        .build()
    )

    track_handler = ConversationHandler(
        entry_points=[CommandHandler('track', track_start)],
        states={
            TrackState.INIT_CHOICE: [
                CallbackQueryHandler(track_init_choice),
                MessageHandler(filters.ALL & ~filters.COMMAND, button_notify_handler)
            ],
            TrackState.MOVIE: [MessageHandler(filters.TEXT & ~filters.COMMAND, track_movie)],
            TrackState.MOVIE_CHOICE: [
                CallbackQueryHandler(track_movie_choice),
                MessageHandler(filters.ALL & ~filters.COMMAND, button_notify_handler)
            ],
            TrackState.TV_SHOW: [MessageHandler(filters.TEXT & ~filters.COMMAND, track_tv_show)],
            TrackState.TV_SHOW_CHOICE: [
                CallbackQueryHandler(track_tv_show_choice),
                MessageHandler(filters.ALL & ~filters.COMMAND, button_notify_handler)
            ],
            TrackState.LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, track_link)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_handler),
            MessageHandler(filters.ALL, invalid_answer_handler)
        ]
    )

    stop_handler = ConversationHandler(
        entry_points=[CommandHandler('stop', stop_start)],
        states={0: [CallbackQueryHandler(stop_choice)]},
        fallbacks=[
            CommandHandler('cancel', cancel_handler),
            MessageHandler(filters.ALL, button_notify_handler)
        ]
    )

    application.add_handler(CommandHandler('start', start_handler))
    application.add_handler(track_handler)
    application.add_handler(stop_handler)
    application.add_handler(CommandHandler('shows', shows_handler))
    application.add_handler(CommandHandler('help', help_handler))
    application.add_handler(MessageHandler(
        filters.COMMAND,
        callback=lambda update, _: update.message.reply_text("Unknown command, see /help")
    ))
    application.add_handler(MessageHandler(
        filters.ALL,
        callback=lambda update, _: update.message.reply_text("Not a command, see /help")
    ))
    application.add_error_handler(error_handler)

    application.job_queue.run_daily(send_releases, time(hour=16, minute=0))

    application.run_polling()


if __name__ == '__main__':
    main()
