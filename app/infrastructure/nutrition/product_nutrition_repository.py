from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.db.models import ProductNutrition, ProductNutritionMatch
from app.db.nutrition_columns import INTEGER_NUTRITION_KEYS, MEAL_ITEM_NUTRITION_KEYS
from app.infrastructure.nutrition.csv_nutrition_provider import safe_float

VALID_MATCH_STATUSES = frozenset({"matched", "manual", "fallback_csv"})
USDA_VALID_MATCH_STATUSES = frozenset({"matched"})


def normalize_product_query(value: str | None) -> str:
    """Lowercase, strip, collapse whitespace."""
    return " ".join((value or "").strip().lower().split())


def get_product_match(
    db: Session,
    *,
    normalized_query: str,
    state: str,
    source: str = "usda_fdc",
) -> ProductNutritionMatch | None:
    query = (
        db.query(ProductNutritionMatch)
        .options(joinedload(ProductNutritionMatch.product))
        .filter(
            ProductNutritionMatch.normalized_query == normalized_query,
            ProductNutritionMatch.state == (state or "unknown"),
            ProductNutritionMatch.source == source,
        )
    )
    if source == "usda_fdc":
        query = query.filter(ProductNutritionMatch.match_status.in_(USDA_VALID_MATCH_STATUSES))
    else:
        query = query.filter(ProductNutritionMatch.match_status.in_(VALID_MATCH_STATUSES))
    return query.first()


def _apply_nutrients_to_product(product: ProductNutrition, nutrients_per_100g: dict[str, Any]) -> None:
    for key in MEAL_ITEM_NUTRITION_KEYS:
        if key not in nutrients_per_100g:
            continue
        val = nutrients_per_100g[key]
        if val is None:
            setattr(product, key, None)
            continue
        num = safe_float(val)
        if key in INTEGER_NUTRITION_KEYS:
            setattr(product, key, int(round(num)))
        elif key == "fiber_g":
            setattr(product, key, round(num, 2))
        else:
            setattr(product, key, round(num, 3))


def upsert_product_nutrition(
    db: Session,
    *,
    source: str,
    source_food_id: str | None,
    normalized_query: str | None,
    state: str,
    description: str,
    data_type: str | None,
    food_category: str | None,
    match_score: float | None,
    match_status: str,
    nutrients_per_100g: dict[str, Any],
    raw_source: dict[str, Any] | None,
) -> ProductNutrition:
    product: ProductNutrition | None = None
    if source_food_id:
        product = (
            db.query(ProductNutrition)
            .filter(ProductNutrition.source == source, ProductNutrition.source_food_id == str(source_food_id))
            .first()
        )
    if product is None:
        product = ProductNutrition(source=source, source_food_id=str(source_food_id) if source_food_id else None)
        db.add(product)

    product.normalized_query = normalize_product_query(normalized_query) if normalized_query else None
    product.state = state or "unknown"
    product.description = description
    product.data_type = data_type
    product.food_category = food_category
    product.match_score = match_score
    product.match_status = match_status
    product.nutrients_per_100g_json = json.dumps(nutrients_per_100g, ensure_ascii=False)
    product.raw_source_json = json.dumps(raw_source or {}, ensure_ascii=False)
    _apply_nutrients_to_product(product, nutrients_per_100g)
    product.updated_at = datetime.utcnow()
    db.flush()
    return product


def upsert_product_match(
    db: Session,
    *,
    normalized_query: str,
    state: str,
    source: str,
    product_nutrition_id: int,
    match_score: float | None,
    match_status: str,
    selected_description: str | None,
    selected_source_food_id: str | None,
    selected_data_type: str | None,
) -> ProductNutritionMatch:
    nq = normalize_product_query(normalized_query)
    st = state or "unknown"
    match = (
        db.query(ProductNutritionMatch)
        .filter(
            ProductNutritionMatch.normalized_query == nq,
            ProductNutritionMatch.state == st,
            ProductNutritionMatch.source == source,
        )
        .first()
    )
    if match is None:
        match = ProductNutritionMatch(
            normalized_query=nq,
            state=st,
            source=source,
            product_nutrition_id=product_nutrition_id,
        )
        db.add(match)

    match.product_nutrition_id = product_nutrition_id
    match.match_score = match_score
    match.match_status = match_status
    match.selected_description = selected_description
    match.selected_source_food_id = selected_source_food_id
    match.selected_data_type = selected_data_type
    match.updated_at = datetime.utcnow()
    db.flush()
    return match


def product_nutrition_to_per_100g_dict(product: ProductNutrition) -> dict[str, float]:
    """Return all non-null nutrient fields as dict."""
    out: dict[str, float] = {}
    if product.nutrients_per_100g_json:
        try:
            parsed = json.loads(product.nutrients_per_100g_json)
            if isinstance(parsed, dict):
                for key, val in parsed.items():
                    if key in MEAL_ITEM_NUTRITION_KEYS and val is not None:
                        out[key] = safe_float(val)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    for key in MEAL_ITEM_NUTRITION_KEYS:
        if key in out:
            continue
        val = getattr(product, key, None)
        if val is not None:
            out[key] = safe_float(val)
    return out


def scale_product_nutrition(product: ProductNutrition, grams: float) -> dict[str, Any]:
    """Scale product per-100g nutrient fields to portion grams."""
    per_100g = product_nutrition_to_per_100g_dict(product)
    weight = safe_float(grams)
    scaled: dict[str, Any] = {}
    for key, value in per_100g.items():
        portion = value * weight / 100.0
        if key in INTEGER_NUTRITION_KEYS:
            scaled[key] = int(round(portion))
        elif key == "fiber_g":
            scaled[key] = round(portion, 2)
        else:
            scaled[key] = round(portion, 3)
    return scaled
