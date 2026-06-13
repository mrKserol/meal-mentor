from __future__ import annotations

import logging
from typing import Any

from app.core.config import USDA_API_KEY
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
}


class NutritionService2:
    """
    USDA FoodData Central nutrition provider.
    Interface intentionally mirrors CSV NutritionService where possible.
    """

    def __init__(self, client: UsdaFoodDataClient | None = None):
        self._client = client or UsdaFoodDataClient()
        self._matcher = UsdaFoodMatcher(self._client)

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
        normalized = self._matcher.parse_ingredients(ingredients_weights)
        if not normalized:
            return []

        results: list[dict] = []
        for ni in normalized:
            try:
                match = self._matcher.match_ingredient(
                    ni,
                    self._matcher.raw_payload_for(ingredients_weights, ni.input_name),
                )
            except UsdaApiError as exc:
                logger.warning("USDA match failed for %r: %s", ni.input_name, exc)
                results.append({ni.input_name: {}})
                continue
            except Exception as exc:
                logger.exception("Unexpected USDA match failure for %r: %s", ni.input_name, exc)
                results.append({ni.input_name: {}})
                continue

            if not match.nutrients_scaled:
                results.append({ni.input_name: {}})
                continue

            row = dict(match.nutrients_scaled)
            row["match"] = f"USDA: {match.selected_description}" if match.selected_description else "USDA"
            row["weight"] = match.grams
            row["state"] = match.state
            row["match_score"] = match.match_score
            row["fdc_id"] = match.selected_fdc_id
            row["data_type"] = match.selected_data_type
            if include_candidates:
                row["candidates"] = match.candidates
            results.append({ni.input_name: row})
        return results

    def aggregate_nutrition(self, ingredients_weights: dict[str, Any]) -> dict[str, int] | None:
        full = self.aggregate_nutrition_full(ingredients_weights)
        if not full:
            return None
        return {
            "calories": int(round(full.get("calories", 0) or 0)),
            "proteins": int(round(full.get("protein_g", 0) or 0)),
            "fats": int(round(full.get("fat_g", 0) or 0)),
            "carbohydrates": int(round(full.get("carbs_g", 0) or 0)),
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
        return self._matcher.aliases

    @property
    def is_available(self) -> bool:
        return bool(USDA_API_KEY or getattr(self._client, "api_key", None))
