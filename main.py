from asgiref.sync import sync_to_async
import logging
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import api
from db.models import User, Show

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! I'm a bot for tracking releases of new shows")
    if not await sync_to_async(User.objects.filter(id=update.effective_user.id).exists)(): # type: ignore
        await sync_to_async(User(update.effective_user.id).save)() # type: ignore


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add an IMDB title in the format '/add {url}' """
    if len(context.args) != 1:
        await update.message.reply_text("Command is not in the format '/add {url}'")
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

    # TODO: check if movie is already released
    show = Show.create(title)
    await sync_to_async(show.save)()  # type: ignore
    await sync_to_async(show.users.add)(update.effective_user.id)
    await update.message.reply_text(f"Added {title.type} {title.name}")


def main() -> None:
    application = (
        ApplicationBuilder()
        .token('6275382423:AAFWlnD_S2-XtRLY6LOIBIoLeXpx95Z8ySs')
        .build()
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('add', add))

    application.run_polling()


if __name__ == '__main__':
    main()
