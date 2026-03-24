import base64
import logging
from io import BytesIO

import requests
from telegram import Update
from telegram.ext import ContextTypes

from app.core.config import BASE_URL

logger = logging.getLogger(__name__)


def _photo_to_base64(photo_bytes: bytes) -> str:
    return base64.b64encode(photo_bytes).decode("utf-8")


def _call_backend_log(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    image_base64: str,
    file_id: str | None,
) -> tuple[dict | None, str | None]:
    """
    Returns (response_dict, None) on success, or (None, error_message) on failure.
    error_message is user-friendly (e.g. "backend_unavailable").
    """
    url = f"{BASE_URL.rstrip('/')}/meals/log"
    payload = {
        "telegram_id": telegram_id,
        "username": username,
        "first_name": first_name,
        "image_base64": image_base64,
        "telegram_file_id": file_id,
    }
    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError as e:
        logger.warning("Backend unreachable (is it running?): %s", e)
        return None, "backend_unavailable"
    except requests.exceptions.Timeout:
        logger.warning("Backend timeout")
        return None, "timeout"
    except Exception as e:
        logger.exception("Backend /meals/log failed: %s", e)
        return None, "server_error"


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    user = update.effective_user
    if not user:
        return
    await update.message.reply_text("Обрабатываю фото…")
    # Get largest photo size
    photo = update.message.photo[-1]
    try:
        tg_file = await photo.get_file()
        buf = BytesIO()
        await tg_file.download_to_memory(buf)
        image_bytes = buf.getvalue()
    except Exception as e:
        logger.exception("Download photo failed: %s", e)
        await update.message.reply_text("Не удалось скачать фото. Попробуй ещё раз.")
        return
    image_base64 = _photo_to_base64(image_bytes)
    data, err = _call_backend_log(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        image_base64=image_base64,
        file_id=photo.file_id,
    )
    if err:
        if err == "backend_unavailable":
            await update.message.reply_text(
                "Сервер бэкенда недоступен. Запусти его в отдельном терминале:\n"
                "uvicorn service:app --reload\n"
                "или: make backend"
            )
        elif err == "timeout":
            await update.message.reply_text("Сервер слишком долго обрабатывал запрос. Попробуй ещё раз.")
        else:
            await update.message.reply_text("Ошибка сервера. Попробуй позже.")
        return
    if data.get("status") != "success":
        await update.message.reply_text(f"Ошибка анализа: {data.get('error', 'unknown')}")
        return
    ingredients = data.get("result") or {}
    nutrition = data.get("nutrition")
    lines = ["Состав и вес (г):"]
    if ingredients:
        for name, weight in ingredients.items():
            lines.append(f"• {name}: {weight} г")
    else:
        lines.append("Еда не распознана или фото пустое.")
    if nutrition:
        lines.append("")
        lines.append(
            f"Калории: {nutrition.get('calories', 0)} ккал | "
            f"Б: {nutrition.get('proteins', 0)} г | "
            f"Ж: {nutrition.get('fats', 0)} г | "
            f"У: {nutrition.get('carbohydrates', 0)} г"
        )
    lines.append("")
    lines.append("Приём пищи записан в дневник.")
    await update.message.reply_text("\n".join(lines))
