import logging

import requests
from telegram import Update
from telegram.ext import ContextTypes

from app.core.config import BASE_URL
from app.interfaces.telegram.states import USER_STATES, FlowState

logger = logging.getLogger(__name__)


async def save_confirmed_meal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user=None,
) -> bool:
    """Persist meal after user confirmed (callback or typed «да»). Returns True if saved."""
    if user is None:
        user = update.effective_user
    if not user:
        return False

    st = USER_STATES.get(user.id)
    if not st:
        await context.bot.send_message(chat_id=user.id, text="Нет данных для записи. Отправь фото ещё раз.")
        return False

    if st.get("state") not in (
        FlowState.AWAITING_CONFIRMATION,
        FlowState.AWAITING_CONFIRMATION_AFTER_TEXT,
    ):
        await context.bot.send_message(chat_id=user.id, text="Сессия устарела. Отправь фото ещё раз.")
        return False

    meal_data = st.get("meal_data") or {}
    ingredients = meal_data.get("ingredients") or {}
    if not ingredients:
        USER_STATES.pop(user.id, None)
        await context.bot.send_message(chat_id=user.id, text="Нечего записывать. Отправь фото ещё раз.")
        return False

    url = f"{BASE_URL.rstrip('/')}/meals/save"
    payload = {
        "telegram_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "ingredients": ingredients,
        "source_type": meal_data.get("source_type") or "photo",
        "telegram_file_id": meal_data.get("telegram_file_id"),
    }
    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.exception("save meal failed: %s", e)
        await context.bot.send_message(
            chat_id=user.id,
            text="Не удалось записать в дневник. Попробуй позже.",
        )
        return False

    USER_STATES.pop(user.id, None)
    await context.bot.send_message(chat_id=user.id, text="Записал приём пищи в дневник.")
    return True


async def handle_meal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()

    user = update.effective_user
    if not user:
        return

    if query.data == "meal_no":
        USER_STATES.pop(user.id, None)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await context.bot.send_message(chat_id=user.id, text="Ок, не записываю в дневник.")
        return

    if query.data != "meal_yes":
        return

    ok = await save_confirmed_meal(update, context, user)
    if ok:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
