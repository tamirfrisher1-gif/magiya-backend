import logging
from telegram.ext import ApplicationBuilder, CommandHandler

from config.settings import TELEGRAM_BOT_TOKEN
from bot_handlers.commands import ping, help_command
from bot_handlers.rsvp_flow import rsvp_conversation
from bot_handlers.admin import stats, seating

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("seating", seating))
    app.add_handler(rsvp_conversation)

    logger.info("MAGIYA bot is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
