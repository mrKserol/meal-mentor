"""
Central orchestration: vision/text → ingredients → nutrition.csv → optional DB.
No Telegram or HTTP dependencies.
"""

import base64
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.schemas import MacroTotals, MealAnalysisResult, MealLogRequest, MealLogResponse
from app.db.repository import create_meal, get_or_create_user
from app.infrastructure.ai.openai_food_client import OpenAIVisionService
from app.infrastructure.nutrition.csv_nutrition_provider import NutritionService
from app.infrastructure.nutrition.ingredient_input import NormalizedIngredient, parse_ingredients_dict
from app.infrastructure.storage.meal_photo_storage import save_meal_photo_pair

logger = logging.getLogger(__name__)


def _get_vision() -> OpenAIVisionService:
    return OpenAIVisionService()


def _get_nutrition() -> NutritionService:
    return NutritionService()


def _scaled_row_to_nutrition_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Map CSV search row (scaled) to MealItemNutrition kwargs."""
    skip = frozenset({"match", "weight", "state", "match_score", "candidates", "csv_display_name"})
    out: dict[str, Any] = {}
    if "calories" in row and row["calories"] is not None:
        out["calories"] = int(row["calories"])
    if "proteins" in row and row["proteins"] is not None:
        out["protein_g"] = int(row["proteins"])
    if "fats" in row and row["fats"] is not None:
        out["fat_g"] = int(row["fats"])
    if "carbohydrates" in row and row["carbohydrates"] is not None:
        out["carbs_g"] = int(row["carbohydrates"])
    if "fiber_g" in row and row["fiber_g"] is not None:
        out["fiber_g"] = round(float(row["fiber_g"]), 2)
    int_micro = ("sugar_g", "sodium_mg")
    for k in int_micro:
        if k in row and row[k] is not None:
            out[k] = int(round(float(row[k])))
    float_keys = (
        "saturated_fat_g",
        "calcium_mg",
        "magnesium_mg",
        "potassium_mg",
        "phosphorus_mg",
        "iron_mg",
        "zinc_mg",
        "selenium_mcg",
        "copper_mg",
        "manganese_mg",
        "vitamin_a_mcg",
        "vitamin_c_mg",
        "vitamin_d_mcg",
        "vitamin_e_mg",
        "vitamin_k_mcg",
        "vitamin_b6_mg",
        "vitamin_b12_mcg",
        "folate_mcg",
        "thiamin_mg",
        "riboflavin_mg",
        "niacin_mg",
        "pantothenic_acid_mg",
        "choline_mg",
    )
    for k in float_keys:
        if k in row and row[k] is not None and k not in skip:
            out[k] = float(row[k])
    return out


def _build_meal_items(ingredients: dict[str, Any], nutrition_svc: NutritionService) -> list[dict[str, Any]]:
    """Map ingredients dict to rows for create_meal."""
    items: list[dict[str, Any]] = []
    lookup: dict[str, dict[str, Any]] = {}
    norm_by_name: dict[str, NormalizedIngredient] = {}
    if ingredients:
        norm_by_name = {ni.input_name: ni for ni in parse_ingredients_dict(ingredients, nutrition_svc.aliases)}
    if nutrition_svc.is_available and ingredients:
        detailed = nutrition_svc.search(ingredients, search_type="fuzzy")
        for block in detailed:
            for ing_name, data in block.items():
                if data and isinstance(data, dict):
                    lookup[ing_name] = data

    for name in (ingredients or {}).keys():
        if not isinstance(name, str) or not name.strip():
            continue
        sk = name.strip()
        ni = norm_by_name.get(sk)
        w = int(ni.grams) if ni is not None else None
        if w is None and sk in lookup and lookup[sk].get("weight") is not None:
            try:
                w = int(float(lookup[sk]["weight"]))
            except (TypeError, ValueError):
                w = None
        if w is None and ni is None and not isinstance((ingredients or {}).get(name), dict):
            try:
                w = int(float((ingredients or {}).get(name)))
            except (TypeError, ValueError):
                w = None
        row = lookup.get(sk, {})
        nutrition = _scaled_row_to_nutrition_dict(row) if row else None
        if nutrition == {}:
            nutrition = None
        ing_state = ni.state if ni is not None else None
        items.append(
            {
                "item_name": name,
                "estimated_weight_g": w,
                "ingredient_state": ing_state,
                "nutrition": nutrition,
            }
        )
    return items


def build_meal_item_specs_from_ingredients(ingredients: dict[str, Any]) -> list[dict[str, Any]]:
    """Build persistable line items from an ingredients dict (for appending to an existing meal)."""
    return _build_meal_items(ingredients, _get_nutrition())


def _meal_result_from_vision_dict(out: dict[str, Any]) -> MealAnalysisResult:
    if out.get("status") != "success":
        return MealAnalysisResult(
            status="error",
            ingredients={},
            confidence=None,
            prediction=None,
            error=out.get("error") or "unknown",
        )
    ingredients = out.get("ingredients") or {}
    if not isinstance(ingredients, dict):
        ingredients = {}
    conf = out.get("confidence")
    pred = out.get("prediction")
    prediction = pred.strip() if isinstance(pred, str) and pred.strip() else None
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
        prediction=prediction,
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


def resolve_meal_photo_urls_for_save(
    user_id: int,
    *,
    image_base64: str | None,
    meal_photo_large: str | None,
    meal_photo_thumb: str | None,
) -> tuple[str | None, str | None]:
    """Decode optional base64; save originals if no explicit URLs provided."""
    lg = meal_photo_large
    th = meal_photo_thumb
    if image_base64 and not lg:
        image_bytes = decode_optional_image_b64(image_base64)
        if image_bytes:
            try:
                saved = save_meal_photo_pair(image_bytes, user_id=user_id)
                lg = saved.get("meal_photo_large")
                th = saved.get("meal_photo_thumb")
            except Exception as e:
                logger.exception("Failed to save meal photo: %s", e)
                lg = None
                th = None
    return lg, th


def decode_optional_image_b64(raw: str | None) -> bytes | None:
    if not raw or not str(raw).strip():
        return None
    try:
        normalized = "".join(str(raw).strip().split())
        padded = normalized + "=" * (-len(normalized) % 4)
        out = base64.b64decode(padded, validate=True)
        if len(out) > 15 * 1024 * 1024:
            return None
        return out
    except Exception:
        return None


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
    lg, th = resolve_meal_photo_urls_for_save(
        user.id,
        image_base64=req.image_base64,
        meal_photo_large=req.meal_photo_large,
        meal_photo_thumb=req.meal_photo_thumb,
    )
    create_meal(
        db,
        user.id,
        source_type=req.source_type,
        meal_datetime=datetime.utcnow(),
        telegram_file_id=req.telegram_file_id,
        prediction=req.prediction,
        user_text=req.user_text,
        meal_photo_large=lg,
        meal_photo_thumb=th,
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
    pred = payload.get("prediction")
    prediction_val = pred if isinstance(pred, str) and pred.strip() else None
    save = persist_meal_to_database(
        db,
        MealLogRequest(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            ingredients=ingredients,
            source_type="photo",
            telegram_file_id=telegram_file_id,
            prediction=prediction_val,
            image_base64=image_base64,
        ),
    )
    save_d = save.to_api_dict()
    if save_d.get("status") != "success":
        payload["status"] = "error"
        payload["error"] = save_d.get("error", "save failed")
    return payload
