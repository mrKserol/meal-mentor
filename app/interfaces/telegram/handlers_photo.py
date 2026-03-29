import base64
import logging
from io import BytesIO

import requests
from telegram import Update
from telegram.ext import ContextTypes

from app.core.config import BASE_URL, LOW_CONFIDENCE_THRESHOLD
from app.interfaces.telegram.states import USER_STATES, FlowState, UIMode
from app.interfaces.telegram.telegram_formatters import format_recognition_question, kb_recognition_confirm

logger = logging.getLogger(__name__)


def _photo_to_base64(photo_bytes: bytes) -> str:
    return base64.b64encode(photo_bytes).decode("utf-8")


def _post_analyze(image_base64: str) -> tuple[dict | None, str | None]:
    url = f"{BASE_URL.rstrip('/')}/meals/analyze"
    try:
        r = requests.post(url, json={"image_base64": image_base64}, timeout=120)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError as e:
        logger.warning("Backend unreachable: %s", e)
        return None, "backend_unavailable"
    except requests.exceptions.Timeout:
        return None, "timeout"
    except Exception as e:
        logger.exception("Analyze failed: %s", e)
        return None, "server_error"


def _needs_user_description(ingredients: dict, confidence: float | None) -> bool:
    if not ingredients:
        return True
    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        return True
    return False


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    user = update.effective_user
    if not user:
        return

    st = USER_STATES.get(user.id) or {}
    if st.get("state") != FlowState.MEAL_ADD_WAITING_INPUT:
        return

    st = USER_STATES.setdefault(user.id, {})
    st["mode"] = UIMode.DIARY_ADD_MEAL
    st["state"] = FlowState.MEAL_ADD_WAITING_INPUT
    for k in ("meal_data", "context"):
        st.pop(k, None)

    await update.message.reply_text("Обрабатываю фото…")
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
    data, err = _post_analyze(image_base64)
    if err:
        if err == "backend_unavailable":
            await update.message.reply_text(
                "Сервер бэкенда недоступен. Запусти uvicorn service:app или проверь BASE_URL."
            )
        elif err == "timeout":
            await update.message.reply_text("Сервер слишком долго обрабатывал запрос. Попробуй ещё раз.")
        else:
            await update.message.reply_text("Ошибка сервера. Попробуй позже.")
        return

    if data.get("status") != "success":
        await update.message.reply_text(f"Ошибка анализа: {data.get('error', 'unknown')}")
        return

    ingredients = data.get("ingredients") or {}
    if not isinstance(ingredients, dict):
        ingredients = {}
    confidence = data.get("confidence")
    nutrition = data.get("nutrition")

    if _needs_user_description(ingredients, confidence):
        USER_STATES[user.id].update(
            {
                "mode": UIMode.DIARY_ADD_MEAL,
                "state": FlowState.MEAL_ADD_TEXT_MANUAL,
                "context": {
                    "telegram_file_id": photo.file_id,
                    "source_type": "photo",
                },
            }
        )
        await update.message.reply_text(
            "Распознавание неуверенное или пустое.\n"
            "Опиши блюдо текстом — что на фото и примерные порции."
        )
        return

    meal_data = {
        "ingredients": ingredients,
        "confidence": confidence,
        "nutrition": nutrition,
        "telegram_file_id": photo.file_id,
        "source_type": "photo",
    }
    USER_STATES[user.id]["meal_data"] = meal_data
    USER_STATES[user.id]["state"] = FlowState.MEAL_ADD_RECOGNITION_CHECK
    await update.message.reply_text(
        format_recognition_question(ingredients),
        reply_markup=kb_recognition_confirm(),
    )
