"""
Aggregate stored meal nutrients for charts, reports, future insights.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.db.models import Meal, MealItem
from app.db.nutrition_columns import MEAL_ITEM_NUTRITION_KEYS
from app.db.repository import get_user_by_telegram_id


def _sum_item_nutrition(n) -> dict[str, float]:
    out: dict[str, float] = {}
    if n is None:
        return out
    for k in MEAL_ITEM_NUTRITION_KEYS:
        v = getattr(n, k, None)
        if v is not None:
            out[k] = out.get(k, 0.0) + float(v)
    return out


def aggregate_meals_total(
    db: Session,
    telegram_id: int,
    days: int = 7,
) -> dict[str, Any]:
    """Sum all MealItemNutrition fields for user's meals in window."""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {"totals": {}, "meals_count": 0, "days": days}
    since = datetime.utcnow() - timedelta(days=days)
    meals = (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user.id, Meal.meal_datetime >= since)
        .order_by(Meal.meal_datetime.desc())
        .limit(500)
        .all()
    )
    totals: dict[str, float] = {}
    for meal in meals:
        for item in meal.items:
            part = _sum_item_nutrition(item.nutrition)
            for k, v in part.items():
                totals[k] = totals.get(k, 0.0) + v
    # Aliases for charts
    out = dict(totals)
    if "protein_g" in out:
        out["proteins"] = out["protein_g"]
    if "fat_g" in out:
        out["fats"] = out["fat_g"]
    if "carbs_g" in out:
        out["carbohydrates"] = out["carbs_g"]
    return {
        "totals": out,
        "meals_count": len(meals),
        "days": days,
    }


def aggregate_meals_by_day(
    db: Session,
    telegram_id: int,
    days: int = 7,
) -> list[dict[str, Any]]:
    """Per UTC date aggregates (macros) for stacked / multi-day charts."""
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return []
    since = datetime.utcnow() - timedelta(days=days)
    meals = (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user.id, Meal.meal_datetime >= since)
        .all()
    )
    by_day: dict[date, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for meal in meals:
        d = meal.meal_datetime.date()
        for item in meal.items:
            n = item.nutrition
            if not n:
                continue
            by_day[d]["calories"] += float(n.calories or 0)
            by_day[d]["protein_g"] += float(n.protein_g or 0)
            by_day[d]["fat_g"] += float(n.fat_g or 0)
            by_day[d]["carbs_g"] += float(n.carbs_g or 0)
            by_day[d]["fiber_g"] += float(n.fiber_g or 0)
    return [
        {
            "date": str(d),
            "calories": v["calories"],
            "protein_g": v["protein_g"],
            "fat_g": v["fat_g"],
            "carbs_g": v["carbs_g"],
            "fiber_g": v["fiber_g"],
        }
        for d, v in sorted(by_day.items(), key=lambda x: x[0])
    ]


def micronutrient_totals_for_insights(
    db: Session,
    telegram_id: int,
    days: int = 7,
) -> dict[str, float]:
    """Flat sums of all stored micronutrient columns (future recommendation engine)."""
    agg = aggregate_meals_total(db, telegram_id, days=days)
    return {k: v for k, v in agg["totals"].items() if k not in ("calories", "protein_g", "fat_g", "carbs_g")}
