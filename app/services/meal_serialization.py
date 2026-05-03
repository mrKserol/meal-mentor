"""Shared meal → UI strings (дневник, списки по дню)."""

from __future__ import annotations

from app.db.models import Meal


def meal_composition_line(meal: Meal) -> str:
    parts: list[str] = []
    for it in meal.items:
        name = (it.item_name or "").strip()
        if not name:
            continue
        w = it.estimated_weight_g
        if w is not None:
            try:
                parts.append(f"{name} {int(round(float(w)))} г")
            except (TypeError, ValueError):
                parts.append(name)
        else:
            parts.append(name)
    return ", ".join(parts) if parts else "—"


def meal_total_calories(meal: Meal) -> int:
    c = 0
    for item in meal.items:
        n = item.nutrition
        if n is None:
            continue
        c += n.calories or 0
    return c
