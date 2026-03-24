from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.db.models import Meal, MealItem
from app.db.repository import get_user_by_telegram_id


def get_report(
    db: Session,
    telegram_id: int,
    days: int = 7,
) -> dict[str, Any]:
    """
    Aggregates meals for the last `days` days from MealItemNutrition rows.
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
    meals = (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user.id, Meal.meal_datetime >= since)
        .order_by(Meal.meal_datetime.desc())
        .limit(500)
        .all()
    )

    total_calories = 0
    total_proteins = 0
    total_fats = 0
    total_carbs = 0

    for meal in meals:
        for item in meal.items:
            n = item.nutrition
            if n is None:
                continue
            total_calories += n.calories or 0
            total_proteins += n.protein_g or 0
            total_fats += n.fat_g or 0
            total_carbs += n.carbs_g or 0

    daily = (
        {
            "calories": round(total_calories / days, 0),
            "proteins": round(total_proteins / days, 0),
            "fats": round(total_fats / days, 0),
            "carbohydrates": round(total_carbs / days, 0),
        }
        if days > 0
        else {}
    )
    return {
        "total_calories": total_calories,
        "total_proteins": total_proteins,
        "total_fats": total_fats,
        "total_carbohydrates": total_carbs,
        "meals_count": len(meals),
        "days": days,
        "daily_avg": daily,
    }
