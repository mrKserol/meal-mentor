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
from app.infrastructure.nutrition.csv_nutrition_provider import NutritionService, safe_float
from app.infrastructure.nutrition.ingredient_input import NormalizedIngredient, parse_ingredients_dict
from app.infrastructure.storage.meal_photo_storage import save_meal_photo_pair

logger = logging.getLogger(__name__)

NUTRIENT_FIELD_MAP: dict[str, str] = {
    "calories": "calories",
    "proteins": "protein_g",
    "fats": "fat_g",
    "total_fat_g": "total_fat_g",
    "carbohydrates": "carbs_g",
    "fiber_g": "fiber_g",
    "sugar_g": "sugar_g",
    "sodium_mg": "sodium_mg",
    "saturated_fat_g": "saturated_fat_g",
    "saturated_fatty_acids_g": "saturated_fatty_acids_g",
    "monounsaturated_fatty_acids_g": "monounsaturated_fatty_acids_g",
    "polyunsaturated_fatty_acids_g": "polyunsaturated_fatty_acids_g",
    "fatty_acids_total_trans_mg": "fatty_acids_total_trans_mg",
    "serving_size_g": "serving_size_g",
    "cholesterol_mg": "cholesterol_mg",
    "choline_mg": "choline_mg",
    "folate_mcg": "folate_mcg",
    "folic_acid_mcg": "folic_acid_mcg",
    "niacin_mg": "niacin_mg",
    "pantothenic_acid_mg": "pantothenic_acid_mg",
    "riboflavin_mg": "riboflavin_mg",
    "thiamin_mg": "thiamin_mg",
    "vitamin_a_iu": "vitamin_a_iu",
    "vitamin_a_rae_mcg": "vitamin_a_rae_mcg",
    "carotene_alpha_mcg": "carotene_alpha_mcg",
    "carotene_beta_mcg": "carotene_beta_mcg",
    "cryptoxanthin_beta_mcg": "cryptoxanthin_beta_mcg",
    "lutein_zeaxanthin_mcg": "lutein_zeaxanthin_mcg",
    "lycopene_mcg": "lycopene_mcg",
    "vitamin_b12_mcg": "vitamin_b12_mcg",
    "vitamin_b6_mg": "vitamin_b6_mg",
    "vitamin_c_mg": "vitamin_c_mg",
    "vitamin_d_iu": "vitamin_d_iu",
    "vitamin_e_mg": "vitamin_e_mg",
    "tocopherol_alpha_mg": "tocopherol_alpha_mg",
    "vitamin_k_mcg": "vitamin_k_mcg",
    "calcium_mg": "calcium_mg",
    "copper_mg": "copper_mg",
    "iron_mg": "iron_mg",
    "magnesium_mg": "magnesium_mg",
    "manganese_mg": "manganese_mg",
    "phosphorus_mg": "phosphorus_mg",
    "potassium_mg": "potassium_mg",
    "selenium_mcg": "selenium_mcg",
    "zinc_mg": "zinc_mg",
    "alanine_g": "alanine_g",
    "arginine_g": "arginine_g",
    "aspartic_acid_g": "aspartic_acid_g",
    "cystine_g": "cystine_g",
    "glutamic_acid_g": "glutamic_acid_g",
    "glycine_g": "glycine_g",
    "histidine_g": "histidine_g",
    "hydroxyproline_g": "hydroxyproline_g",
    "isoleucine_g": "isoleucine_g",
    "leucine_g": "leucine_g",
    "lysine_g": "lysine_g",
    "methionine_g": "methionine_g",
    "phenylalanine_g": "phenylalanine_g",
    "proline_g": "proline_g",
    "serine_g": "serine_g",
    "threonine_g": "threonine_g",
    "tryptophan_g": "tryptophan_g",
    "tyrosine_g": "tyrosine_g",
    "valine_g": "valine_g",
    "fructose_g": "fructose_g",
    "galactose_g": "galactose_g",
    "glucose_g": "glucose_g",
    "lactose_g": "lactose_g",
    "maltose_g": "maltose_g",
    "sucrose_g": "sucrose_g",
    "alcohol_g": "alcohol_g",
    "ash_g": "ash_g",
    "caffeine_mg": "caffeine_mg",
    "theobromine_mg": "theobromine_mg",
    "water_g": "water_g",
}

_INT_NUTRIENT_COLUMNS = frozenset({"calories", "protein_g", "fat_g", "carbs_g", "sugar_g", "sodium_mg"})


def _get_vision() -> OpenAIVisionService:
    return OpenAIVisionService()


def _get_nutrition() -> NutritionService:
    return NutritionService()


def _scaled_row_to_nutrition_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Map CSV search row (scaled) to MealItemNutrition kwargs."""
    out: dict[str, Any] = {}
    for src_field, dst_field in NUTRIENT_FIELD_MAP.items():
        if src_field not in row:
            continue
        val = safe_float(row.get(src_field))
        if dst_field in _INT_NUTRIENT_COLUMNS:
            out[dst_field] = int(round(val))
        elif dst_field == "fiber_g":
            out[dst_field] = round(val, 2)
        else:
            out[dst_field] = round(val, 3)

    if "fat_g" not in out:
        out["fat_g"] = int(round(safe_float(row.get("fats") or row.get("total_fat_g"))))
    if "total_fat_g" not in out:
        out["total_fat_g"] = round(safe_float(row.get("total_fat_g") or row.get("fats")), 3)
    if "saturated_fat_g" not in out:
        out["saturated_fat_g"] = round(
            safe_float(row.get("saturated_fat_g") or row.get("saturated_fatty_acids_g")),
            3,
        )
    if "saturated_fatty_acids_g" not in out:
        out["saturated_fatty_acids_g"] = round(
            safe_float(row.get("saturated_fatty_acids_g") or row.get("saturated_fat_g")),
            3,
        )
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
    nutrition_full: dict[str, float] | None = None
    if nutrition_svc.is_available and ingredients:
        agg = nutrition_svc.aggregate_nutrition(ingredients)
        nutrition_full = nutrition_svc.aggregate_nutrition_full(ingredients)
        if agg is not None:
            nutrition = MacroTotals(**agg)
    return MealAnalysisResult(
        status="success",
        ingredients=ingredients,
        confidence=conf,
        nutrition=nutrition,
        nutrition_full=nutrition_full,
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
