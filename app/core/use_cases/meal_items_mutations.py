"""Add/remove lines on an existing logged meal."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.use_cases.meal_analysis import analyze_meal_from_text, build_meal_item_specs_from_ingredients
from app.db.repository import (
    append_meal_item_rows,
    delete_meal_item_for_user,
    get_user_by_telegram_id,
)


def remove_meal_item(db: Session, telegram_id: int, meal_id: int, item_id: int) -> dict[str, Any]:
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {"status": "error", "error": "user not found"}
    ok = delete_meal_item_for_user(db, meal_id, user.id, item_id)
    return {"status": "ok" if ok else "error", "error": "" if ok else "not found"}


def add_meal_items_from_text_description(
    db: Session,
    telegram_id: int,
    meal_id: int,
    description: str,
) -> dict[str, Any]:
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {"status": "error", "error": "user not found"}
    analyzed = analyze_meal_from_text(description.strip())
    if analyzed.status != "success":
        return {"status": "error", "error": analyzed.error or "analysis failed"}
    ingredients = analyzed.ingredients or {}
    if not ingredients:
        return {"status": "error", "error": "no ingredients parsed"}
    specs = build_meal_item_specs_from_ingredients(ingredients)
    if not specs:
        return {"status": "error", "error": "empty specs"}
    ok = append_meal_item_rows(db, meal_id, user.id, specs)
    return {"status": "ok" if ok else "error", "error": "" if ok else "append failed", "items_added": len(specs)}
