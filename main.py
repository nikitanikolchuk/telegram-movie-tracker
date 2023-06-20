import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from asgiref.sync import sync_to_async

from db.models import Title

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! I'm a bot for tracking releases of new shows")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add an IMDB title in the format '/add {id}' """
    # TODO: change to accept URL
    try:
        # TODO: change to fetch data from API
        imdb_id = context.args[0]
        await sync_to_async(Title.create(imdb_id).save)()
    except IndexError:
        await update.message.reply_text("Incorrect format")
        return
    except ValueError:
        await update.message.reply_text("Incorrect id")
        return
    await update.message.reply_text(f"Saved title with id {context.args[0]}")


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
