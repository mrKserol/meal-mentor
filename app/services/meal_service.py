from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.repository import create_meal, get_or_create_user
from app.services.openai_vision import OpenAIVisionService
from app.services.nutrition_service import NutritionService


def _get_vision() -> OpenAIVisionService:
    return OpenAIVisionService()


def _get_nutrition() -> NutritionService:
    return NutritionService()


def _build_meal_items(ingredients: dict[str, Any], nutrition_svc: NutritionService) -> list[dict[str, Any]]:
    """Map vision ingredients dict to rows for create_meal."""
    items: list[dict[str, Any]] = []
    lookup: dict[str, dict[str, Any]] = {}
    if nutrition_svc.is_available and ingredients:
        detailed = nutrition_svc.search(ingredients, search_type="fuzzy")
        for block in detailed:
            for ing_name, data in block.items():
                if data and isinstance(data, dict):
                    lookup[ing_name] = data

    for name, weight in (ingredients or {}).items():
        w = None
        try:
            w = int(float(weight)) if weight is not None else None
        except (TypeError, ValueError):
            w = None
        row = lookup.get(name, {})
        nutrition = None
        if row:
            nutrition = {
                "calories": row.get("calories"),
                "protein_g": row.get("proteins"),
                "fat_g": row.get("fats"),
                "carbs_g": row.get("carbohydrates"),
            }
        items.append(
            {
                "item_name": name,
                "estimated_weight_g": w,
                "nutrition": nutrition,
            }
        )
    return items


def analyze_photo(image_base64: str) -> dict[str, Any]:
    """
    Runs vision on photo and optionally nutrition aggregation.
    Returns { status, result: { ingredient: weight }, nutrition?: { calories, ... }, error? }.
    """
    vision = _get_vision()
    out = vision.analyze_image(image_base64)
    if out["status"] != "success":
        return out
    ingredients = out.get("result") or {}
    if not isinstance(ingredients, dict):
        ingredients = {}
    nutrition_svc = _get_nutrition()
    if nutrition_svc.is_available:
        agg = nutrition_svc.aggregate_nutrition(ingredients)
        if agg is not None:
            out["nutrition"] = agg
    return out


def log_meal(
    db: Session,
    telegram_id: int,
    username: str | None,
    image_base64: str,
    telegram_file_id: str | None = None,
    *,
    first_name: str | None = None,
) -> dict[str, Any]:
    """
    Analyze photo, persist Meal + MealItem + MealItemNutrition, return same payload as analyze_photo.
    """
    payload = analyze_photo(image_base64)
    if payload["status"] != "success":
        return payload
    ingredients = payload.get("result") or {}
    if not isinstance(ingredients, dict):
        ingredients = {}

    user = get_or_create_user(
        db,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
    )
    nutrition_svc = _get_nutrition()
    items = _build_meal_items(ingredients, nutrition_svc)

    create_meal(
        db,
        user.id,
        source_type="photo",
        meal_datetime=datetime.utcnow(),
        telegram_file_id=telegram_file_id,
        items=items,
    )
    return payload
