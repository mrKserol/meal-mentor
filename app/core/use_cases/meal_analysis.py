"""
Central orchestration: vision/text → ingredients → nutrition.csv → optional DB.
No Telegram or HTTP dependencies.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.schemas import MacroTotals, MealAnalysisResult, MealLogRequest, MealLogResponse
from app.db.repository import create_meal, get_or_create_user
from app.infrastructure.ai.openai_food_client import OpenAIVisionService
from app.infrastructure.nutrition.csv_nutrition_provider import NutritionService


def _get_vision() -> OpenAIVisionService:
    return OpenAIVisionService()


def _get_nutrition() -> NutritionService:
    return NutritionService()


def _build_meal_items(ingredients: dict[str, Any], nutrition_svc: NutritionService) -> list[dict[str, Any]]:
    """Map ingredients dict to rows for create_meal."""
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


def _meal_result_from_vision_dict(out: dict[str, Any]) -> MealAnalysisResult:
    if out.get("status") != "success":
        return MealAnalysisResult(
            status="error",
            ingredients={},
            confidence=None,
            error=out.get("error") or "unknown",
        )
    ingredients = out.get("ingredients") or {}
    if not isinstance(ingredients, dict):
        ingredients = {}
    conf = out.get("confidence")
    nutrition_svc = _get_nutrition()
    nutrition = None
    if nutrition_svc.is_available and ingredients:
        agg = nutrition_svc.aggregate_nutrition(ingredients)
        if agg is not None:
            nutrition = MacroTotals(**agg)
    return MealAnalysisResult(
        status="success",
        ingredients=ingredients,
        confidence=conf,
        nutrition=nutrition,
        error="",
    )


def analyze_meal_from_image_base64(image_base64: str) -> MealAnalysisResult:
    """1) Vision 2) normalize (in client) 3) nutrition lookup 4) return structured result."""
    vision = _get_vision()
    raw = vision.analyze_image(image_base64)
    return _meal_result_from_vision_dict(raw)


def analyze_meal_from_text(user_text: str) -> MealAnalysisResult:
    """Same pipeline as photo, text-only model call."""
    vision = _get_vision()
    raw = vision.analyze_text(user_text)
    return _meal_result_from_vision_dict(raw)


def persist_meal_to_database(db: Session, req: MealLogRequest) -> MealLogResponse:
    """Log confirmed meal after user approval (any channel)."""
    ingredients = req.ingredients
    if not ingredients or not isinstance(ingredients, dict):
        return MealLogResponse(status="error", error="ingredients required")
    user = get_or_create_user(
        db,
        telegram_id=req.telegram_id,
        username=req.username,
        first_name=req.first_name,
    )
    nutrition_svc = _get_nutrition()
    items = _build_meal_items(ingredients, nutrition_svc)
    create_meal(
        db,
        user.id,
        source_type=req.source_type,
        meal_datetime=datetime.utcnow(),
        telegram_file_id=req.telegram_file_id,
        items=items,
    )
    return MealLogResponse(status="success")


def analyze_and_log_meal_legacy(
    db: Session,
    telegram_id: int,
    username: str | None,
    image_base64: str,
    telegram_file_id: str | None = None,
    *,
    first_name: str | None = None,
) -> dict[str, Any]:
    """
    One-shot: analyze photo + save (legacy /meals/log).
    Returns the same dict shape as historical API (including possible mutation on save error).
    """
    analyzed = analyze_meal_from_image_base64(image_base64)
    payload = analyzed.to_api_dict()
    if payload["status"] != "success":
        return payload
    ingredients = payload.get("ingredients") or {}
    save = persist_meal_to_database(
        db,
        MealLogRequest(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            ingredients=ingredients,
            source_type="photo",
            telegram_file_id=telegram_file_id,
        ),
    )
    save_d = save.to_api_dict()
    if save_d.get("status") != "success":
        payload["status"] = "error"
        payload["error"] = save_d.get("error", "save failed")
    return payload
