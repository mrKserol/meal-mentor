import logging

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.core.config import TELEGRAM_BOT_TOKEN
from app.interfaces.telegram.states import USER_STATES
from app.interfaces.telegram.handlers_start import cmd_start
from app.interfaces.telegram.handlers_photo import handle_photo
from app.interfaces.telegram.handlers_reports import cmd_report
from app.interfaces.telegram.handlers_callbacks import handle_meal_callback
from app.interfaces.telegram.handlers_text_flow import handle_text_flow, meal_flow_text

# Алиас для отладки (тот же объект, что USER_STATES)
user_states = USER_STATES

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
    app.add_handler(CallbackQueryHandler(handle_meal_callback, pattern=r"^meal_(yes|no)$"))
    app.add_handler(
        MessageHandler(
            meal_flow_text & filters.TEXT & ~filters.COMMAND,
            handle_text_flow,
        )
    )
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return app


def run_polling() -> None:
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_polling()
