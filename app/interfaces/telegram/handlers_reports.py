import requests
from telegram import Update
from telegram.ext import ContextTypes

from app.core.config import BASE_URL


def _call_backend_report(telegram_id: int, days: int) -> dict | None:
    url = f"{BASE_URL.rstrip('/')}/reports/summary"
    try:
        r = requests.get(url, params={"telegram_id": telegram_id, "days": days}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    days = 7
    if context.args and context.args[0].isdigit():
        days = max(1, min(365, int(context.args[0])))
    user_id = update.effective_user.id
    data = _call_backend_report(user_id, days)
    if data is None:
        await update.message.reply_text("Не удалось загрузить отчёт. Проверь, что бэкенд запущен.")
        return
    total_c = data.get("total_calories", 0)
    total_p = data.get("total_proteins", 0)
    total_f = data.get("total_fats", 0)
    total_carb = data.get("total_carbohydrates", 0)
    meals = data.get("meals_count", 0)
    daily = data.get("daily_avg") or {}
    msg = (
        f"Сводка за последние {days} дн.:\n\n"
        f"Приёмов пищи: {meals}\n"
        f"Калории всего: {total_c} ккал\n"
        f"Белки: {total_p} г | Жиры: {total_f} г | Углеводы: {total_carb} г\n"
    )
    if daily:
        msg += (
            f"\nВ среднем в день:\n"
            f"Калории: {daily.get('calories', 0)} ккал | "
            f"Б: {daily.get('proteins', 0)} г | "
            f"Ж: {daily.get('fats', 0)} г | У: {daily.get('carbohydrates', 0)} г"
        )
    await update.message.reply_text(msg)
