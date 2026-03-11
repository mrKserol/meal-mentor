import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.core.config import TELEGRAM_BOT_TOKEN
from app.bot.handlers_start import cmd_start
from app.bot.handlers_photo import handle_photo
from app.bot.handlers_reports import cmd_report

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return app


def run_polling() -> None:
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_polling()
