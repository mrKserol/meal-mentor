import logging

import requests
from telegram import Update
from telegram.ext import ContextTypes, filters

from app.core.config import BASE_URL, LOW_CONFIDENCE_THRESHOLD
from app.interfaces.telegram.states import USER_STATES, FlowState
from app.interfaces.telegram.meal_messages import format_meal_reply
from app.interfaces.telegram.meal_messages import CONFIRM_KEYBOARD
from app.interfaces.telegram.handlers_callbacks import save_confirmed_meal

logger = logging.getLogger(__name__)


class MealFlowTextFilter(filters.MessageFilter):
    """Only messages from users in an active meal-confirmation / description flow."""

    __slots__ = ()

    def filter(self, message):
        user = message.from_user
        if not user:
            return False
        st = USER_STATES.get(user.id)
        if not st:
            return False
        return st.get("state") in (
            FlowState.AWAITING_DESCRIPTION,
            FlowState.AWAITING_CONFIRMATION,
            FlowState.AWAITING_CONFIRMATION_AFTER_TEXT,
        )


meal_flow_text = MealFlowTextFilter()


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

    if state == FlowState.AWAITING_DESCRIPTION:
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
                "По этому описанию не удалось выделить еду. Попробуй переформулировать подробнее."
            )
            return

        ctx = st.get("context") or {}
        meal_data = {
            "ingredients": ingredients,
            "confidence": confidence,
            "nutrition": nutrition,
            "telegram_file_id": ctx.get("telegram_file_id"),
            "source_type": "text",
        }
        USER_STATES[user.id] = {
            "state": FlowState.AWAITING_CONFIRMATION_AFTER_TEXT,
            "meal_data": meal_data,
        }
        await update.message.reply_text(
            format_meal_reply(ingredients, nutrition),
            reply_markup=CONFIRM_KEYBOARD,
        )
        return

    if state in (FlowState.AWAITING_CONFIRMATION, FlowState.AWAITING_CONFIRMATION_AFTER_TEXT):
        low = text.lower()
        if low in ("да", "yes", "y"):
            await save_confirmed_meal(update, context, user)
        elif low in ("нет", "no", "n"):
            USER_STATES.pop(user.id, None)
            await update.message.reply_text("Ок, не записываю в дневник.")
        else:
            await update.message.reply_text(
                "Ответь «да» или «нет», либо нажми кнопку под предыдущим сообщением."
            )
        return
