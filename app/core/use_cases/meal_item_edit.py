"""Recalculate stored meal line item when weight changes."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.use_cases.meal_analysis import _scaled_row_to_nutrition_dict
from app.db.repository import get_meal_by_id_for_user, get_user_by_telegram_id, update_meal_item_weight
from app.infrastructure.nutrition.csv_nutrition_provider import NutritionService


def recalculate_meal_item_weight(
    db: Session,
    telegram_id: int,
    meal_id: int,
    item_id: int,
    new_weight_g: int,
) -> dict[str, Any]:
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {"status": "error", "error": "user not found"}
    meal = get_meal_by_id_for_user(db, meal_id, user.id)
    if not meal:
        return {"status": "error", "error": "meal not found"}
    item = next((i for i in meal.items if i.id == item_id), None)
    if not item:
        return {"status": "error", "error": "item not found"}
    svc = NutritionService()
    if not svc.is_available:
        ok = update_meal_item_weight(
            db,
            meal_id,
            user.id,
            item_id,
            new_weight_g,
            nutrition=None,
        )
        return {"status": "ok" if ok else "error", "note": "nutrition csv unavailable"}
    state = getattr(item, "ingredient_state", None) or "unknown"
    rows = svc.search({item.item_name: {"grams": new_weight_g, "state": state}}, search_type="fuzzy")
    row: dict[str, Any] = {}
    for block in rows:
        for _k, data in block.items():
            if data and isinstance(data, dict):
                row = data
                break
    nut = _scaled_row_to_nutrition_dict(row) if row else {}
    ok = update_meal_item_weight(
        db,
        meal_id,
        user.id,
        item_id,
        new_weight_g,
        nutrition=nut if nut else None,
    )
    return {"status": "ok" if ok else "error", "nutrition": nut}
