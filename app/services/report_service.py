import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db.repository import get_user_by_telegram_id, get_meal_logs


def get_report(
    db: Session,
    telegram_id: int,
    days: int = 7,
) -> dict[str, Any]:
    """
    Aggregates meal logs for the last `days` days.
    Returns { total_calories, total_proteins, total_fats, total_carbohydrates, meals_count, daily_avg }.
    """
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {
            "total_calories": 0,
            "total_proteins": 0,
            "total_fats": 0,
            "total_carbohydrates": 0,
            "meals_count": 0,
            "daily_avg": {},
        }
    since = datetime.utcnow() - timedelta(days=days)
    logs = get_meal_logs(db, user.id, since=since, limit=500)
    total = {"calories": 0, "proteins": 0, "fats": 0, "carbohydrates": 0}
    for log in logs:
        try:
            nut = json.loads(log.nutrition_json)
            for k in total:
                total[k] += nut.get(k, 0) or 0
        except (json.JSONDecodeError, TypeError):
            continue
    daily = (
        {
            "calories": round(total["calories"] / days, 0),
            "proteins": round(total["proteins"] / days, 0),
            "fats": round(total["fats"] / days, 0),
            "carbohydrates": round(total["carbohydrates"] / days, 0),
        }
        if days > 0
        else {}
    )
    return {
        "total_calories": total["calories"],
        "total_proteins": total["proteins"],
        "total_fats": total["fats"],
        "total_carbohydrates": total["carbohydrates"],
        "meals_count": len(logs),
        "days": days,
        "daily_avg": daily,
    }
