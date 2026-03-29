import logging

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from app.core.config import TELEGRAM_BOT_TOKEN
from app.interfaces.telegram.states import USER_STATES, FlowState
from app.interfaces.telegram.handlers_menu import (
    build_profile_numeric_handler,
    cmd_start,
    menu_callback,
    photo_outside_diary,
)
from app.interfaces.telegram.handlers_photo import handle_photo
from app.interfaces.telegram.handlers_reports import cmd_report
from app.interfaces.telegram.handlers_callbacks import handle_meal_callback
from app.interfaces.telegram.handlers_text_flow import handle_text_flow, meal_flow_text
from app.interfaces.telegram.states import UIMode

user_states = USER_STATES

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def _photo_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    st = USER_STATES.get(user.id) if user else None
    if (
        st
        and st.get("mode") == UIMode.DIARY_ADD_MEAL
        and st.get("state") == FlowState.MEAL_ADD_WAITING_INPUT
    ):
        await handle_photo(update, context)
    else:
        await photo_outside_diary(update, context)


def build_application() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^(m:|c:)"))
    app.add_handler(CallbackQueryHandler(handle_meal_callback, pattern=r"^meal_(yes|no|rec_yes|rec_no)$"))
    app.add_handler(build_profile_numeric_handler())
    app.add_handler(
        MessageHandler(
            meal_flow_text & filters.TEXT & ~filters.COMMAND,
            handle_text_flow,
        )
    )
    app.add_handler(MessageHandler(filters.PHOTO, _photo_router))
    return app


def run_polling() -> None:
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_polling()
