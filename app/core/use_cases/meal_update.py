"""Replace all line items on an existing meal (web diary edit)."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.use_cases.meal_analysis import build_meal_item_specs_from_ingredients
from app.db.repository import get_meal_by_id_for_user, replace_meal_items_for_user


def update_meal_composition(
    db: Session,
    user_id: int,
    meal_id: int,
    ingredients: dict[str, Any],
    prediction: str | None = None,
) -> dict[str, Any]:
    if not ingredients:
        return {"status": "error", "error": "ingredients required"}

    meal = get_meal_by_id_for_user(db, meal_id, user_id)
    if not meal:
        return {"status": "error", "error": "meal not found"}

    specs = build_meal_item_specs_from_ingredients(ingredients)
    if not specs:
        return {"status": "error", "error": "empty specs"}

    pred = prediction.strip() if isinstance(prediction, str) and prediction.strip() else None
    ok = replace_meal_items_for_user(db, meal_id, user_id, specs, prediction=pred)
    return {"status": "ok" if ok else "error", "error": "" if ok else "update failed"}
