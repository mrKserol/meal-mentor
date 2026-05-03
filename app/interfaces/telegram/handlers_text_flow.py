import logging

import requests
from telegram import Update
from telegram.ext import ContextTypes, filters

from app.core.config import BASE_URL, LOW_CONFIDENCE_THRESHOLD
from app.interfaces.telegram.states import USER_STATES, FlowState, UIMode
from app.interfaces.telegram.telegram_formatters import (
    format_meal_analyzed_detail,
    format_recognition_question,
    kb_recognition_confirm,
    kb_save_meal_confirm,
)
from app.interfaces.telegram.handlers_callbacks import save_confirmed_meal

logger = logging.getLogger(__name__)


class MealFlowTextFilter(filters.MessageFilter):
    __slots__ = ()

    def filter(self, message):
        user = message.from_user
        if not user:
            return False
        st = USER_STATES.get(user.id)
        if not st:
            return False
        if st.get("mode") != UIMode.DIARY_ADD_MEAL:
            return False
        return st.get("state") in (
            FlowState.MEAL_ADD_WAITING_INPUT,
            FlowState.MEAL_ADD_TEXT_MANUAL,
            FlowState.MEAL_ADD_SAVE_CONFIRMATION,
        )


meal_flow_text = MealFlowTextFilter()


def _prediction_from_api(data: dict | None) -> str | None:
    if not data:
        return None
    p = data.get("prediction")
    return p.strip() if isinstance(p, str) and p.strip() else None


def _post_analyze_text(text: str) -> tuple[dict | None, str | None]:
    url = f"{BASE_URL.rstrip('/')}/meals/analyze-text"
    try:
        r = requests.post(url, json={"text": text}, timeout=120)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "backend_unavailable"
    except requests.exceptions.Timeout:
        return None, "timeout"
    except Exception as e:
        logger.exception("analyze-text failed: %s", e)
        return None, "server_error"


def _needs_user_description(ingredients: dict, confidence: float | None) -> bool:
    if not ingredients:
        return True
    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        return True
    return False


async def handle_text_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    user = update.effective_user
    if not user:
        return

    text = update.message.text.strip()
    if not text:
        return

    st = USER_STATES.get(user.id)
    if not st:
        return

    state = st.get("state")

    if state == FlowState.MEAL_ADD_WAITING_INPUT:
        await update.message.reply_text("Анализирую описание…")
        data, err = _post_analyze_text(text)
        if err:
            if err == "backend_unavailable":
                await update.message.reply_text("Бэкенд недоступен. Проверь BASE_URL.")
            elif err == "timeout":
                await update.message.reply_text("Таймаут. Попробуй ещё раз.")
            else:
                await update.message.reply_text("Ошибка сервера.")
            return
        if data.get("status") != "success":
            await update.message.reply_text(f"Ошибка: {data.get('error', 'unknown')}")
            return

        ingredients = data.get("ingredients") or {}
        confidence = data.get("confidence")
        nutrition = data.get("nutrition")

        if _needs_user_description(ingredients, confidence):
            await update.message.reply_text(
                "По описанию мало данных. Добавь деталей: что именно и сколько примерно по весу."
            )
            return

        meal_data = {
            "ingredients": ingredients,
            "confidence": confidence,
            "nutrition": nutrition,
            "telegram_file_id": None,
            "source_type": "text",
            "prediction": _prediction_from_api(data),
            "user_text": text,
        }
        USER_STATES[user.id]["meal_data"] = meal_data
        USER_STATES[user.id]["state"] = FlowState.MEAL_ADD_RECOGNITION_CHECK
        await update.message.reply_text(
            format_recognition_question(_prediction_from_api(data), ingredients),
            reply_markup=kb_recognition_confirm(),
        )
        return

    if state == FlowState.MEAL_ADD_TEXT_MANUAL:
        await update.message.reply_text("Анализирую описание…")
        data, err = _post_analyze_text(text)
        if err:
            if err == "backend_unavailable":
                await update.message.reply_text("Бэкенд недоступен. Проверь BASE_URL.")
            elif err == "timeout":
                await update.message.reply_text("Таймаут. Попробуй ещё раз.")
            else:
                await update.message.reply_text("Ошибка сервера.")
            return
        if data.get("status") != "success":
            await update.message.reply_text(f"Ошибка: {data.get('error', 'unknown')}")
            return

        ingredients = data.get("ingredients") or {}
        confidence = data.get("confidence")
        nutrition = data.get("nutrition")

        if _needs_user_description(ingredients, confidence):
            await update.message.reply_text(
                "Не получилось выделить еду. Переформулируй подробнее (продукты и граммы)."
            )
            return

        ctx = st.get("context") or {}
        pred = _prediction_from_api(data)
        if not pred:
            cr = ctx.get("prediction")
            pred = cr.strip() if isinstance(cr, str) and cr.strip() else None
        meal_data = {
            "ingredients": ingredients,
            "confidence": confidence,
            "nutrition": nutrition,
            "telegram_file_id": ctx.get("telegram_file_id"),
            "source_type": "text",
            "prediction": pred,
            "user_text": text,
            "image_base64": ctx.get("image_base64"),
        }
        USER_STATES[user.id]["meal_data"] = meal_data
        USER_STATES[user.id]["state"] = FlowState.MEAL_ADD_SAVE_CONFIRMATION
        USER_STATES[user.id].pop("context", None)
        await update.message.reply_text(
            format_meal_analyzed_detail(ingredients, nutrition),
            reply_markup=kb_save_meal_confirm(),
        )
        return

    if state == FlowState.MEAL_ADD_SAVE_CONFIRMATION:
        low = text.lower()
        if low in ("да", "yes", "y"):
            await save_confirmed_meal(update, context, user)
        elif low in ("нет", "no", "n"):
            USER_STATES[user.id] = {"mode": UIMode.IDLE}
            await update.message.reply_text("Ок, не записываю в дневник.")
        else:
            await update.message.reply_text(
                "Ответь «да» или «нет», либо нажми кнопку под предыдущим сообщением."
            )
        return
