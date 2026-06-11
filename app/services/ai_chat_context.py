from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.db.models import AdditiveIntake, Allergen, Meal, MealItem, User
from app.services.additive_totals import list_additive_intakes_for_range
from app.services.nutrition_targets import get_active_nutrition_target
from app.services.user_timezone import resolve_tz, utc_naive_to_local

# TODO: move shared nutrition/date helpers to app/services/nutrition_periods.py
from app.services.diary_snapshot import _meal_list_title, _meal_naive_dt, _sum_meal_nutrition
from app.services.meal_serialization import meal_composition_line
from app.db.repository import list_user_measurements


def _age_years(birth: date | None, today: date) -> int | None:
    if birth is None:
        return None
    years = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    return max(0, years)


def _period_14d(user: User) -> tuple[datetime, datetime, date, date, Any]:
    tz = resolve_tz(user)
    today = datetime.now(tz).date()
    first = today - timedelta(days=13)
    tomorrow = today + timedelta(days=1)
    start_local = datetime.combine(first, datetime.min.time(), tzinfo=tz)
    end_local = datetime.combine(tomorrow, datetime.min.time(), tzinfo=tz)
    return start_local.astimezone(timezone.utc).replace(tzinfo=None), end_local.astimezone(timezone.utc).replace(tzinfo=None), first, today, tz


def _float_or_none(value: Any) -> float | None:
    return float(value) if value is not None else None


def build_ai_chat_context(db: Session, user: User) -> dict:
    start_utc, end_utc, first_day, last_day, tz = _period_14d(user)
    today_local = datetime.now(tz).date()

    allergens = [
        row.allergen_key
        for row in db.query(Allergen).filter(Allergen.user_id == user.id).order_by(Allergen.allergen_key).all()
    ]

    target = get_active_nutrition_target(db, user_id=user.id)
    targets = {
        "calories_kcal": getattr(target, "target_calories", None),
        "protein_g": getattr(target, "target_protein_g", None),
        "fat_g": getattr(target, "target_fat_g", None),
        "carbs_g": getattr(target, "target_carbs_g", None),
        "fiber_g": getattr(target, "target_fiber_g", None),
    }

    meals = (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user.id, Meal.meal_datetime >= start_utc, Meal.meal_datetime < end_utc)
        .order_by(Meal.meal_datetime.desc())
        .all()
    )

    by_day: dict[date, dict[str, Any]] = defaultdict(
        lambda: {
            "calories_kcal": 0,
            "protein_g": 0,
            "fat_g": 0,
            "carbs_g": 0,
            "fiber_g": 0.0,
            "sugar_g": 0.0,
            "sodium_mg": 0.0,
            "saturated_fat_g": 0.0,
            "water_ml": 0.0,
            "meals_count": 0,
        }
    )
    recent_meals: list[dict[str, Any]] = []

    for meal in meals:
        local = utc_naive_to_local(_meal_naive_dt(meal), tz)
        d = local.date()
        if d < first_day or d > last_day:
            continue
        totals = _sum_meal_nutrition(meal)
        day = by_day[d]
        day["calories_kcal"] += int(totals["calories"])
        day["protein_g"] += int(totals["protein_g"])
        day["fat_g"] += int(totals["fat_g"])
        day["carbs_g"] += int(totals["carbs_g"])
        day["fiber_g"] += float(totals["fiber_g"])
        day["sugar_g"] += float(totals["sugar_g"])
        day["sodium_mg"] += float(totals["sodium_mg"])
        day["saturated_fat_g"] += float(totals["saturated_fat_g"])
        day["water_ml"] += float(totals.get("water_g", 0) or 0)
        day["meals_count"] += 1

        if len(recent_meals) < 20:
            recent_meals.append(
                {
                    "datetime_local": local.isoformat(),
                    "meal_name": _meal_list_title(meal),
                    "user_text": meal.user_text,
                    "composition": meal_composition_line(meal),
                    "calories_kcal": int(totals["calories"]),
                    "protein_g": int(totals["protein_g"]),
                    "fat_g": int(totals["fat_g"]),
                    "carbs_g": int(totals["carbs_g"]),
                    "fiber_g": float(totals["fiber_g"]),
                    "sugar_g": float(totals["sugar_g"]),
                    "sodium_mg": float(totals["sodium_mg"]),
                    "saturated_fat_g": float(totals["saturated_fat_g"]),
                }
            )

    intakes = list_additive_intakes_for_range(db, user.id, start_utc, end_utc)
    supplements_14d: list[dict[str, Any]] = []
    supplement_days: set[date] = set()
    for intake in intakes:
        local = utc_naive_to_local(intake.intake_datetime.replace(tzinfo=None), tz)
        d = local.date()
        if d < first_day or d > last_day:
            continue
        supplement_days.add(d)
        day = by_day[d]
        day["calories_kcal"] += int(round(float(intake.calories or 0)))
        day["protein_g"] += int(round(float(intake.protein_g or 0)))
        day["fat_g"] += int(round(float(intake.fat_g or 0)))
        day["carbs_g"] += int(round(float(intake.carbs_g or 0)))
        day["fiber_g"] += float(intake.fiber_g or 0)
        day["water_ml"] += float(intake.water_g or 0)
        supplements_14d.append(
            {
                "date": d.isoformat(),
                "datetime_local": local.isoformat(),
                "name": intake.additive_name_snapshot,
                "servings_count": float(intake.servings_count or 0),
                "calories_kcal": int(round(float(intake.calories or 0))),
                "protein_g": int(round(float(intake.protein_g or 0))),
                "fat_g": int(round(float(intake.fat_g or 0))),
                "carbs_g": int(round(float(intake.carbs_g or 0))),
                "fiber_g": float(intake.fiber_g or 0),
            }
        )

    daily_summary = []
    total_water = 0.0
    days_with_water = 0
    days_with_food_logs = 0
    for i in range(14):
        d = first_day + timedelta(days=i)
        raw = by_day.get(d)
        if not raw:
            continue
        if raw["meals_count"] > 0:
            days_with_food_logs += 1
        if raw["water_ml"] > 0:
            total_water += float(raw["water_ml"])
            days_with_water += 1
        daily_summary.append(
            {
                "date": d.isoformat(),
                "calories_kcal": int(raw["calories_kcal"]),
                "protein_g": int(raw["protein_g"]),
                "fat_g": int(raw["fat_g"]),
                "carbs_g": int(raw["carbs_g"]),
                "fiber_g": round(float(raw["fiber_g"]), 2),
                "sugar_g": round(float(raw["sugar_g"]), 2),
                "sodium_mg": round(float(raw["sodium_mg"]), 2),
                "saturated_fat_g": round(float(raw["saturated_fat_g"]), 2),
                "meals_count": int(raw["meals_count"]),
            }
        )

    measurements = [
        m
        for m in list_user_measurements(db, user.id, limit=1000)
        if m.weight_kg is not None and start_utc <= m.measured_at.replace(tzinfo=None) < end_utc
    ]
    measurements_asc = sorted(measurements, key=lambda item: item.measured_at)
    last_weigh_ins = [
        {"date": utc_naive_to_local(m.measured_at.replace(tzinfo=None), tz).date().isoformat(), "weight_kg": float(m.weight_kg)}
        for m in measurements_asc[-10:]
    ]
    trend_14d_kg = (
        round(float(measurements_asc[-1].weight_kg) - float(measurements_asc[0].weight_kg), 2)
        if len(measurements_asc) >= 2
        else None
    )

    has_profile = all(
        value is not None
        for value in (user.sex, user.birth_date, user.height_cm, user.weight_kg, user.activity_level)
    )

    return {
        "user_profile": {
            "age": _age_years(user.birth_date, today_local),
            "sex": user.sex,
            "height_cm": user.height_cm,
            "current_weight_kg": _float_or_none(user.weight_kg),
            "target_weight_kg": _float_or_none(user.target_weight_kg),
            "goal": user.goal,
            "activity_level": user.activity_level,
            "timezone": user.timezone,
            "language": user.language or "ru",
            "allergens": allergens,
            "restrictions": [],
            "preferences": [],
        },
        "nutrition_targets": targets,
        "nutrition_14d": {
            "from": first_day.isoformat(),
            "to": last_day.isoformat(),
            "days_with_food_logs": days_with_food_logs,
            "daily_summary": daily_summary,
            "recent_meals": recent_meals,
        },
        "weight": {
            "current_weight_kg": _float_or_none(user.weight_kg),
            "target_weight_kg": _float_or_none(user.target_weight_kg),
            "last_weigh_ins": last_weigh_ins,
            "trend_14d_kg": trend_14d_kg,
        },
        "supplements_14d": supplements_14d,
        "water": {
            "avg_daily_water_ml_14d": round(total_water / days_with_water, 1) if days_with_water else None,
            "note": "water from meal/additive water_g if available; explicit water logs are not implemented yet",
        },
        "data_quality": {
            "has_profile": has_profile,
            "has_targets": target is not None,
            "days_with_food_logs": days_with_food_logs,
            "days_with_weight_logs": len({item["date"] for item in last_weigh_ins}),
            "days_with_supplement_logs": len(supplement_days),
        },
    }
