"""Команда /check_ingredients и обработка фото этикетки (без meal flow и БД)."""

import logging
from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

from app.interfaces.telegram.states import USER_STATES, UIMode
from app.services.ingredient_checker import analyze_label_from_image_bytes, format_label_result_for_telegram

logger = logging.getLogger(__name__)


CHECK_INGREDIENTS_INVITE = (
    "📸 Сфотографируй этикетку с составом продукта, и я проверю ингредиенты."
)


async def cmd_check_ingredients(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    uid = update.effective_user.id
    USER_STATES[uid] = {"mode": UIMode.CHECK_INGREDIENTS}
    await update.message.reply_text(CHECK_INGREDIENTS_INVITE)


def _reset_idle(uid: int) -> None:
    USER_STATES[uid] = {"mode": UIMode.IDLE}


async def handle_ingredients_label_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    user = update.effective_user
    if not user:
        return
    uid = user.id
    st = USER_STATES.get(uid) or {}
    if st.get("mode") != UIMode.CHECK_INGREDIENTS:
        return

    await update.message.reply_text("Проверяю этикетку…")
    photo = update.message.photo[-1]
    try:
        tg_file = await photo.get_file()
        buf = BytesIO()
        await tg_file.download_to_memory(buf)
        image_bytes = buf.getvalue()
    except Exception as e:
        logger.exception("label photo download: %s", e)
        _reset_idle(uid)
        await update.message.reply_text("Не удалось скачать фото. Попробуй ещё раз.")
        return

    try:
        data = analyze_label_from_image_bytes(image_bytes)
        text = format_label_result_for_telegram(data)
    except Exception as e:
        logger.exception("ingredient checker: %s", e)
        _reset_idle(uid)
        await update.message.reply_text("Произошла ошибка при анализе. Попробуй позже.")
        return

    _reset_idle(uid)
    if len(text) > 4090:
        text = text[:4075] + "\n…"
    await update.message.reply_text(text)
