from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import PROMPT_USDA_V2_PATH
from app.core.schemas import MacroTotals, MealAnalysisResult, MealLogRequest, MealLogResponse
from app.core.use_cases.meal_analysis import (
    _normalize_meal_item_confidence,
    _scaled_row_to_nutrition_dict,
    build_meal_items_with_nutrition_provider,
    enrich_meal_display_fields,
    resolve_meal_photo_urls_for_save,
)
from app.db.models import ProductNutrition
from app.db.repository import create_meal, get_or_create_user
from app.infrastructure.ai.openai_food_client import OpenAIVisionService
from app.infrastructure.nutrition.product_nutrition_repository import scale_product_nutrition
from app.infrastructure.nutrition.usda_nutrition_provider import NutritionService2

logger = logging.getLogger(__name__)


def _get_vision_v2() -> OpenAIVisionService:
    return OpenAIVisionService(prompt_path=PROMPT_USDA_V2_PATH)


def _get_nutrition_v2(db: Session | None = None) -> NutritionService2:
    return NutritionService2(db=db)


def _enrich_ingredients_with_search_trace(
    ingredients: dict[str, Any],
    search_blocks: list[dict],
) -> dict[str, Any]:
    lookup: dict[str, dict[str, Any]] = {}
    for block in search_blocks:
        for name, row in block.items():
            if isinstance(row, dict):
                lookup[name] = row

    enriched: dict[str, Any] = {}
    for name, payload in (ingredients or {}).items():
        if isinstance(payload, dict):
            entry = dict(payload)
        else:
            entry = {"grams": payload, "state": "unknown"}
        row = lookup.get(name, {})
        if row:
            for key in (
                "product_nutrition_id",
                "product_nutrition_match_id",
                "nutrition_source",
                "nutrition_pipeline_version",
                "nutrition_match_score",
                "nutrition_match_status",
                "source",
            ):
                if key in row:
                    entry[key] = row[key]
            if row.get("usda_search_query") and not entry.get("usda_search_query"):
                entry["usda_search_query"] = row["usda_search_query"]
            if row.get("confidence") is not None and entry.get("confidence") is None:
                entry["confidence"] = row["confidence"]
            match_name = row.get("nutrition_match_name") or row.get("match")
            if match_name:
                entry["nutrition_match_name"] = match_name
        enriched[name] = entry
    return enriched


def meal_result_from_vision_dict_usda(
    out: dict[str, Any],
    *,
    db: Session | None = None,
) -> MealAnalysisResult:
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

    nutrition_svc = _get_nutrition_v2(db)
    nutrition = None
    nutrition_full: dict[str, float] | None = None
    enriched_ingredients = ingredients
    if ingredients:
        search_blocks = nutrition_svc.search(ingredients, search_type="fuzzy")
        enriched_ingredients = _enrich_ingredients_with_search_trace(ingredients, search_blocks)
        nutrition_full = nutrition_svc.aggregate_nutrition_full(ingredients)
        agg = nutrition_svc.aggregate_nutrition(ingredients) if nutrition_full else None
        if agg is not None:
            nutrition = MacroTotals(**agg)

    if ingredients and nutrition is None:
        return MealAnalysisResult(
            status="error",
            ingredients=enriched_ingredients,
            confidence=out.get("confidence"),
            prediction=out.get("prediction"),
            prediction_translated=out.get("prediction_translated"),
            prediction_language=out.get("prediction_language"),
            error="USDA nutrition unavailable",
        )

    pred = out.get("prediction")
    prediction = pred.strip() if isinstance(pred, str) and pred.strip() else None
    pt = out.get("prediction_translated")
    prediction_translated = pt.strip() if isinstance(pt, str) and pt.strip() else None
    pl = out.get("prediction_language")
    prediction_language = pl.strip().lower() if isinstance(pl, str) and pl.strip() else None
    return MealAnalysisResult(
        status="success",
        ingredients=enriched_ingredients,
        confidence=out.get("confidence"),
        nutrition=nutrition,
        nutrition_full=nutrition_full,
        prediction=prediction,
        prediction_translated=prediction_translated,
        prediction_language=prediction_language,
        error="",
    )


def analyze_meal_from_image_base64_v2_usda(
    image_base64: str,
    *,
    db: Session | None = None,
) -> MealAnalysisResult:
    try:
        raw = _get_vision_v2().analyze_image(image_base64)
        return meal_result_from_vision_dict_usda(raw, db=db)
    except Exception as exc:
        logger.exception("V2 USDA image analysis failed: %s", exc)
        return MealAnalysisResult(status="error", ingredients={}, error="V2 USDA image analysis failed")


def analyze_meal_from_text_v2_usda(
    user_text: str,
    *,
    user_language: str | None = "ru",
    db: Session | None = None,
    previous_ingredients: dict[str, Any] | None = None,
    previous_prediction: str | None = None,
    correction: str | None = None,
    correction_history: list[str] | None = None,
) -> MealAnalysisResult:
    try:
        raw = _get_vision_v2().analyze_text(
            user_text,
            previous_ingredients=previous_ingredients,
            previous_prediction=previous_prediction,
            correction=correction,
            correction_history=correction_history,
        )
        result = meal_result_from_vision_dict_usda(raw, db=db)
        return enrich_meal_display_fields(result, user_language=user_language)
    except Exception as exc:
        logger.exception("V2 USDA text analysis failed: %s", exc)
        return MealAnalysisResult(status="error", ingredients={}, error="V2 USDA text analysis failed")


def analyze_meal_from_image_and_text_v2_usda(
    image_base64: str,
    user_text: str,
    previous_ingredients: dict[str, Any] | None = None,
    previous_prediction: str | None = None,
    initial_comment: str | None = None,
    correction_history: list[str] | None = None,
    *,
    db: Session | None = None,
) -> MealAnalysisResult:
    try:
        raw = _get_vision_v2().analyze_image_with_user_text(
            image_base64,
            user_text,
            previous_ingredients=previous_ingredients,
            previous_prediction=previous_prediction,
            initial_comment=initial_comment,
            correction_history=correction_history,
        )
        return meal_result_from_vision_dict_usda(raw, db=db)
    except Exception as exc:
        logger.exception("V2 USDA image+text analysis failed: %s", exc)
        return MealAnalysisResult(status="error", ingredients={}, error="V2 USDA image+text analysis failed")


def recalculate_nutrition_from_ingredients_v2_usda(
    ingredients: dict[str, Any],
    *,
    db: Session | None = None,
) -> MealAnalysisResult:
    if not ingredients or not isinstance(ingredients, dict):
        return MealAnalysisResult(status="success", ingredients={}, nutrition=MacroTotals(), error="")
    try:
        nutrition_svc = _get_nutrition_v2(db)
        search_blocks = nutrition_svc.search(ingredients, search_type="fuzzy")
        enriched = _enrich_ingredients_with_search_trace(ingredients, search_blocks)
        nutrition_full = nutrition_svc.aggregate_nutrition_full(ingredients)
        agg = nutrition_svc.aggregate_nutrition(ingredients) if nutrition_full else None
        if agg is None:
            return MealAnalysisResult(
                status="error",
                ingredients=enriched,
                error="USDA nutrition unavailable",
            )
        return MealAnalysisResult(
            status="success",
            ingredients=enriched,
            nutrition=MacroTotals(**agg),
            nutrition_full=nutrition_full,
            error="",
        )
    except Exception as exc:
        logger.exception("V2 USDA recalculate failed: %s", exc)
        return MealAnalysisResult(status="error", ingredients=ingredients, error="V2 USDA recalculate failed")


def _build_item_from_product_nutrition(
    name: str,
    payload: dict[str, Any],
    product: ProductNutrition,
    db: Session,
) -> dict[str, Any] | None:
    grams = payload.get("grams")
    try:
        weight = int(round(float(grams)))
    except (TypeError, ValueError):
        return None
    scaled = scale_product_nutrition(product, weight)
    nutrition = _scaled_row_to_nutrition_dict(scaled)
    if not nutrition:
        return None
    match_name = payload.get("nutrition_match_name") or f"USDA: {product.description}"
    usda_search_query = payload.get("usda_search_query")
    if isinstance(usda_search_query, str):
        usda_search_query = usda_search_query.strip() or None
    return {
        "item_name": name,
        "estimated_weight_g": weight,
        "ingredient_state": payload.get("state") or product.state,
        "confidence": _normalize_meal_item_confidence(payload.get("confidence")),
        "usda_search_query": usda_search_query,
        "nutrition": nutrition,
        "name_translated": payload.get("name_translated"),
        "name_language": payload.get("name_language"),
        "nutrition_match_name": match_name,
        "nutrition_pipeline_version": payload.get("nutrition_pipeline_version") or "v2_usda",
        "nutrition_source": payload.get("nutrition_source") or "product_nutrition_cache",
    }


def persist_meal_to_database_v2_usda(db: Session, req: MealLogRequest) -> MealLogResponse:
    ingredients = req.ingredients
    if not ingredients or not isinstance(ingredients, dict):
        return MealLogResponse(status="error", error="ingredients required")
    try:
        user = get_or_create_user(
            db,
            telegram_id=req.telegram_id,
            username=req.username,
            first_name=req.first_name,
        )
        items: list[dict[str, Any]] = []
        unresolved: dict[str, Any] = {}
        for name, payload in ingredients.items():
            if not isinstance(name, str) or not name.strip():
                continue
            if isinstance(payload, dict) and payload.get("product_nutrition_id"):
                product = db.query(ProductNutrition).filter(ProductNutrition.id == payload["product_nutrition_id"]).first()
                if product:
                    item = _build_item_from_product_nutrition(name.strip(), payload, product, db)
                    if item:
                        items.append(item)
                        continue
            unresolved[name] = payload

        if unresolved:
            items.extend(
                build_meal_items_with_nutrition_provider(
                    unresolved,
                    _get_nutrition_v2(db),
                )
            )

        if not any(item.get("nutrition") for item in items):
            return MealLogResponse(status="error", error="USDA nutrition unavailable")
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
            prediction_translated=req.prediction_translated,
            prediction_language=req.prediction_language,
            user_text=req.user_text,
            meal_photo_large=lg,
            meal_photo_thumb=th,
            items=items,
        )
        return MealLogResponse(status="success")
    except Exception as exc:
        logger.exception("V2 USDA persist failed: %s", exc)
        db.rollback()
        return MealLogResponse(status="error", error="V2 USDA persist failed")
