import json
from typing import Any

from sqlalchemy.orm import Session

from app.db.repository import get_or_create_user, create_meal_log
from app.services.openai_vision import OpenAIVisionService
from app.services.nutrition_service import NutritionService


def _get_vision() -> OpenAIVisionService:
    return OpenAIVisionService()


def _get_nutrition() -> NutritionService:
    return NutritionService()


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
) -> dict[str, Any]:
    """
    Analyze photo, optionally aggregate nutrition, save to DB, return same payload as analyze_photo.
    """
    payload = analyze_photo(image_base64)
    if payload["status"] != "success":
        return payload
    ingredients = payload.get("result") or {}
    nutrition = payload.get("nutrition") or {}
    user = get_or_create_user(db, telegram_id=telegram_id, username=username)
    create_meal_log(
        db,
        user_id=user.id,
        ingredients=ingredients,
        nutrition=nutrition,
        telegram_file_id=telegram_file_id,
    )
    return payload
