"""Сериализация приёмов за выбранный календарный день (веб / JWT)."""

from __future__ import annotations

from app.db.models import Meal, User
from app.schemas.auth import WebMealDayItemLine, WebMealDayRow
from app.services.diary_snapshot import (
    _absolute_public_url,
    _meal_naive_dt,
    _meal_type_label,
    _resolve_tz,
    _sum_meal_nutrition,
    _utc_naive_to_local,
)
from app.services.meal_serialization import meal_composition_line


def build_web_meal_day_row(meal: Meal, user: User) -> WebMealDayRow:
    tz = _resolve_tz(user)
    local = _utc_naive_to_local(_meal_naive_dt(meal), tz)
    tot = _sum_meal_nutrition(meal)
    sugar_g = 0
    sodium_mg = 0
    saturated_fat_g = 0.0
    lines: list[WebMealDayItemLine] = []
    for it in meal.items:
        n = it.nutrition
        if n is not None:
            sugar_g += int(n.sugar_g or 0)
            sodium_mg += int(n.sodium_mg or 0)
            saturated_fat_g += float(n.saturated_fat_g or 0)
        lines.append(
            WebMealDayItemLine(
                id=it.id,
                item_name=it.item_name,
                estimated_weight_g=it.estimated_weight_g,
                calories=n.calories if n else None,
                protein_g=n.protein_g if n else None,
                fat_g=n.fat_g if n else None,
                carbs_g=n.carbs_g if n else None,
                fiber_g=float(n.fiber_g) if n and n.fiber_g is not None else None,
            )
        )
    return WebMealDayRow(
        id=meal.id,
        prediction=meal.prediction,
        user_text=meal.user_text,
        time_local=local.strftime("%H:%M"),
        meal_type=meal.meal_type,
        meal_type_label=_meal_type_label(meal.meal_type),
        composition=meal_composition_line(meal),
        calories=tot["calories"],
        protein_g=tot["protein_g"],
        fat_g=tot["fat_g"],
        carbs_g=tot["carbs_g"],
        fiber_g=float(tot["fiber_g"]),
        sugar_g=sugar_g,
        sodium_mg=sodium_mg,
        saturated_fat_g=round(saturated_fat_g, 2),
        meal_photo_large=meal.meal_photo_large,
        meal_photo_thumb=meal.meal_photo_thumb,
        meal_photo_large_url=_absolute_public_url(meal.meal_photo_large),
        meal_photo_thumb_url=_absolute_public_url(meal.meal_photo_thumb),
        items=lines,
    )
