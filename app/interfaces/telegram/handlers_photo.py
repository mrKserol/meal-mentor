import base64
import logging
from io import BytesIO

import requests
from telegram import Update
from telegram.ext import ContextTypes

from app.core.config import BASE_URL, LOW_CONFIDENCE_THRESHOLD
from app.interfaces.telegram.states import USER_STATES, FlowState, UIMode
from app.interfaces.telegram.meal_messages import CONFIRM_KEYBOARD, format_meal_reply

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


def _store_confirmation_state(
    user_id: int,
    meal_data: dict,
    state: str = FlowState.AWAITING_CONFIRMATION,
) -> None:
    st = USER_STATES.setdefault(user_id, {})
    st["mode"] = UIMode.DIARY_ADD_MEAL
    st["state"] = state
    st["meal_data"] = meal_data


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.photo:
        return
    user = update.effective_user
    if not user:
        return

    st = USER_STATES.setdefault(user.id, {})
    st["mode"] = UIMode.DIARY_ADD_MEAL
    for k in ("state", "meal_data", "context"):
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
        USER_STATES.setdefault(user.id, {})["mode"] = UIMode.DIARY_ADD_MEAL
        USER_STATES[user.id].update(
            {
                "state": FlowState.AWAITING_DESCRIPTION,
                "context": {
                    "telegram_file_id": photo.file_id,
                    "source_type": "photo",
                },
            }
        )
        await update.message.reply_text(
            "Я не смог распознать еду 😕\n\n"
            "Можешь описать, что на изображении? Например: «паста с курицей и брокколи — одна тарелка»."
        )
        return

    meal_data = {
        "ingredients": ingredients,
        "confidence": confidence,
        "nutrition": nutrition,
        "telegram_file_id": photo.file_id,
        "source_type": "photo",
    }
    _store_confirmation_state(user.id, meal_data, FlowState.AWAITING_CONFIRMATION)
    text = format_meal_reply(ingredients, nutrition)
    await update.message.reply_text(text, reply_markup=CONFIRM_KEYBOARD)
