import logging
import re
from datetime import date

from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from telegram_movie_tracker import api
from telegram_movie_tracker.db.models import User, Show
from telegram_movie_tracker.settings import env

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


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

    try:
        title = api.get_title(match.group('id'))
    except ValueError:
        await update.message.reply_text("Invalid link")
        return

    if title.is_episode:
        await update.message.reply_text("Link points to an episode, send link to a show instead")
        return
    if not title.is_series and title.release_date is not None and title.release_date <= date.today():
        await update.message.reply_text("The show was already released")
        return

    try:
        await Show.objects.track_show(title, update.effective_user.id)
    except ValueError:
        await update.message.reply_text(f"You are already tracking {title.name}")
        return

    await update.message.reply_text(f"Started tracking {title.type} {title.name}")


def main() -> None:
    application = (
        ApplicationBuilder()
        .token(env('BOT_TOKEN'))
        .build()
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('track', track))

    application.run_polling()


if __name__ == '__main__':
    main()
