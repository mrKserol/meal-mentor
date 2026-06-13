from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import USDA_API_KEY, USDA_MIN_MATCH_SCORE
from app.infrastructure.nutrition.csv_nutrition_provider import NutritionService
from app.infrastructure.nutrition.product_nutrition_repository import (
    get_product_match,
    normalize_product_query,
    scale_product_nutrition,
    upsert_product_match,
    upsert_product_nutrition,
)
from app.infrastructure.usda.client import UsdaApiError, UsdaFoodDataClient
from app.infrastructure.usda.food_matcher import UsdaFoodMatcher

logger = logging.getLogger(__name__)

_SKIP_TOTAL_KEYS = {
    "match",
    "weight",
    "state",
    "match_score",
    "fdc_id",
    "data_type",
    "candidates",
    "product_nutrition_id",
    "product_nutrition_match_id",
    "source",
    "nutrition_source",
    "nutrition_match_status",
    "nutrition_match_score",
    "nutrition_match_name",
    "match_status",
    "nutrition_pipeline_version",
}


class NutritionService2:
    """
    USDA FoodData Central nutrition provider with local product_nutrition cache.
    Interface intentionally mirrors CSV NutritionService where possible.
    """

    def __init__(
        self,
        db: Session | None = None,
        matcher: UsdaFoodMatcher | None = None,
        fallback_v1: NutritionService | None = None,
    ):
        self.db = db
        self.matcher = matcher or UsdaFoodMatcher()
        self.fallback_v1 = fallback_v1 or NutritionService()

    def _resolve_normalized_query(self, ni, raw_payload: dict | None) -> str:
        if isinstance(raw_payload, dict):
            raw_query = raw_payload.get("usda_search_query")
            if isinstance(raw_query, str) and raw_query.strip():
                return normalize_product_query(raw_query)
        return normalize_product_query(ni.canonical_query or ni.input_name)

    def _build_trace_row(
        self,
        *,
        scaled: dict[str, Any],
        ni,
        state: str,
        match_label: str,
        match_score: float | None,
        nutrition_source: str,
        nutrition_match_status: str,
        product_nutrition_id: int | None = None,
        product_nutrition_match_id: int | None = None,
        fdc_id: str | None = None,
        data_type: str | None = None,
    ) -> dict[str, Any]:
        row = dict(scaled)
        row["match"] = match_label
        row["weight"] = ni.grams
        row["state"] = state
        row["match_score"] = match_score
        row["nutrition_match_score"] = match_score
        row["nutrition_match_name"] = match_label
        row["nutrition_match_status"] = nutrition_match_status
        row["nutrition_source"] = nutrition_source
        row["nutrition_pipeline_version"] = "v2_usda"
        row["source"] = nutrition_source
        row["match_status"] = nutrition_match_status
        if product_nutrition_id is not None:
            row["product_nutrition_id"] = product_nutrition_id
        if product_nutrition_match_id is not None:
            row["product_nutrition_match_id"] = product_nutrition_match_id
        if fdc_id is not None:
            row["fdc_id"] = fdc_id
        if data_type is not None:
            row["data_type"] = data_type
        return row

    def _try_cached_match(self, ni, raw_payload: dict | None) -> dict[str, Any] | None:
        if self.db is None:
            return None
        normalized_query = self._resolve_normalized_query(ni, raw_payload)
        state = ni.state or "unknown"
        cached = get_product_match(self.db, normalized_query=normalized_query, state=state, source="usda_fdc")
        if cached is None or cached.product is None:
            return None
        product = cached.product
        scaled = scale_product_nutrition(product, ni.grams)
        return self._build_trace_row(
            scaled=scaled,
            ni=ni,
            state=state,
            match_label=f"USDA: {product.description}",
            match_score=cached.match_score,
            nutrition_source="product_nutrition_cache",
            nutrition_match_status=cached.match_status,
            product_nutrition_id=product.id,
            product_nutrition_match_id=cached.id,
            fdc_id=product.source_food_id,
            data_type=product.data_type,
        )

    def _try_v1_fallback(self, ni, ingredients_weights: dict[str, Any], raw_payload: Any) -> dict[str, Any] | None:
        if not self.fallback_v1.is_available:
            return None
        payload = raw_payload if isinstance(raw_payload, dict) else ni.grams
        v1_blocks = self.fallback_v1.search({ni.input_name: payload}, search_type="fuzzy")
        if not v1_blocks:
            return {}
        row = v1_blocks[0].get(ni.input_name, {})
        if not row or not isinstance(row, dict):
            return {}
        if not any(k for k in row if k not in _SKIP_TOTAL_KEYS):
            return {}
        out = dict(row)
        out.setdefault("weight", ni.grams)
        out.setdefault("state", ni.state)
        out["nutrition_pipeline_version"] = "v2_usda"
        out["nutrition_source"] = "local_csv_fallback"
        out["source"] = "local_csv_fallback"
        out["nutrition_match_status"] = "fallback_csv"
        out["match_status"] = "fallback_csv"
        if out.get("match"):
            out["nutrition_match_name"] = out["match"]
        return out

    def _persist_usda_match(
        self,
        ni,
        raw_payload: dict | None,
        usda_result,
    ) -> tuple[dict[str, Any], int | None, int | None]:
        scaled = scale_product_nutrition_from_usda(usda_result.nutrients_per_100g, ni.grams)
        product_id: int | None = None
        match_id: int | None = None
        if self.db is not None:
            product = upsert_product_nutrition(
                self.db,
                source="usda_fdc",
                source_food_id=str(usda_result.selected_fdc_id) if usda_result.selected_fdc_id else None,
                normalized_query=self._resolve_normalized_query(ni, raw_payload),
                state=ni.state or "unknown",
                description=usda_result.selected_description or "USDA food",
                data_type=usda_result.selected_data_type,
                food_category=usda_result.food_category,
                match_score=usda_result.match_score,
                match_status="matched",
                nutrients_per_100g=usda_result.nutrients_per_100g,
                raw_source=usda_result.raw_food_json,
            )
            match = upsert_product_match(
                self.db,
                normalized_query=self._resolve_normalized_query(ni, raw_payload),
                state=ni.state or "unknown",
                source="usda_fdc",
                product_nutrition_id=product.id,
                match_score=usda_result.match_score,
                match_status="matched",
                selected_description=usda_result.selected_description,
                selected_source_food_id=str(usda_result.selected_fdc_id) if usda_result.selected_fdc_id else None,
                selected_data_type=usda_result.selected_data_type,
            )
            scaled = scale_product_nutrition(product, ni.grams)
            product_id = product.id
            match_id = match.id
        else:
            scaled = dict(usda_result.nutrients_scaled)
        row = self._build_trace_row(
            scaled=scaled,
            ni=ni,
            state=ni.state or "unknown",
            match_label=f"USDA: {usda_result.selected_description}" if usda_result.selected_description else "USDA",
            match_score=usda_result.match_score,
            nutrition_source="usda_fdc",
            nutrition_match_status="matched",
            product_nutrition_id=product_id,
            product_nutrition_match_id=match_id,
            fdc_id=str(usda_result.selected_fdc_id) if usda_result.selected_fdc_id else None,
            data_type=usda_result.selected_data_type,
        )
        return row, product_id, match_id

    def search(
        self,
        ingredients_weights: dict[str, Any],
        search_type: str = "fuzzy",
        threshold: float = 0.6,
        *,
        include_candidates: bool = False,
    ) -> list[dict]:
        _ = search_type, threshold
        if not ingredients_weights:
            return []

        normalized = self.matcher.parse_ingredients(ingredients_weights)
        if not normalized:
            return []

        results: list[dict] = []
        for ni in normalized:
            raw_payload = self.matcher.raw_payload_for(ingredients_weights, ni.input_name)
            cached_row = self._try_cached_match(ni, raw_payload)
            if cached_row:
                if include_candidates:
                    cached_row["candidates"] = []
                results.append({ni.input_name: cached_row})
                continue

            usda_result = None
            try:
                usda_result = self.matcher.match_ingredient(ni, raw_payload)
            except UsdaApiError as exc:
                logger.warning("USDA match failed for %r: %s", ni.input_name, exc)
            except Exception as exc:
                logger.exception("Unexpected USDA match failure for %r: %s", ni.input_name, exc)

            if (
                usda_result
                and usda_result.nutrients_per_100g
                and usda_result.match_score >= USDA_MIN_MATCH_SCORE
                and usda_result.match_status == "matched"
            ):
                row, _, _ = self._persist_usda_match(ni, raw_payload, usda_result)
                if include_candidates:
                    row["candidates"] = usda_result.candidates
                results.append({ni.input_name: row})
                continue

            if usda_result and usda_result.match_score < USDA_MIN_MATCH_SCORE:
                logger.info(
                    "USDA low confidence for %r (score=%s), fallback to V1",
                    ni.input_name,
                    usda_result.match_score,
                )

            v1_row = self._try_v1_fallback(ni, ingredients_weights, raw_payload)
            if v1_row:
                results.append({ni.input_name: v1_row})
            else:
                results.append(
                    {
                        ni.input_name: {
                            "nutrition_pipeline_version": "v2_usda",
                            "nutrition_source": "unknown",
                        }
                    }
                )
        return results

    def aggregate_nutrition(self, ingredients_weights: dict[str, Any]) -> dict[str, int] | None:
        full = self.aggregate_nutrition_full(ingredients_weights)
        if not full:
            return None
        proteins = full.get("protein_g", full.get("proteins", 0))
        fats = full.get("fat_g", full.get("fats", 0))
        carbs = full.get("carbs_g", full.get("carbohydrates", 0))
        return {
            "calories": int(round(full.get("calories", 0) or 0)),
            "proteins": int(round(proteins or 0)),
            "fats": int(round(fats or 0)),
            "carbohydrates": int(round(carbs or 0)),
        }

    def aggregate_nutrition_full(self, ingredients_weights: dict[str, Any]) -> dict[str, float] | None:
        if not ingredients_weights:
            return None
        totals: dict[str, float] = {}
        for block in self.search(ingredients_weights, search_type="fuzzy"):
            for _name, row in block.items():
                if not row or not isinstance(row, dict):
                    continue
                for key, value in row.items():
                    if key in _SKIP_TOTAL_KEYS:
                        continue
                    try:
                        totals[key] = totals.get(key, 0.0) + float(value)
                    except (TypeError, ValueError):
                        continue
        return totals if totals else None

    @property
    def aliases(self):
        return self.matcher.aliases

    @property
    def is_available(self) -> bool:
        client = getattr(self.matcher, "client", None)
        return bool(USDA_API_KEY or getattr(client, "api_key", None) or self.fallback_v1.is_available)


def scale_product_nutrition_from_usda(nutrients_per_100g: dict[str, float], grams: int) -> dict[str, Any]:
    from app.db.nutrition_columns import INTEGER_NUTRITION_KEYS

    scaled: dict[str, Any] = {}
    for key, value in nutrients_per_100g.items():
        portion = float(value) * grams / 100.0
        if key in INTEGER_NUTRITION_KEYS:
            scaled[key] = int(round(portion))
        elif key == "fiber_g":
            scaled[key] = round(portion, 2)
        else:
            scaled[key] = round(portion, 3)
    return scaled
