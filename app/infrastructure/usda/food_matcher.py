from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Any

from app.infrastructure.nutrition.food_aliases import FoodAliasIndex
from app.infrastructure.nutrition.ingredient_input import (
    NormalizedIngredient,
    is_beverage_like_query,
    parse_ingredients_dict,
)
from app.infrastructure.usda.client import UsdaApiError, UsdaFoodDataClient
from app.infrastructure.usda.nutrient_mapper import normalize_usda_food_nutrients
from app.infrastructure.usda.schemas import UsdaMatchResult

logger = logging.getLogger(__name__)


DATA_TYPE_SCORES = {
    "Foundation": 1.0,
    "SR Legacy": 0.9,
    "Survey (FNDDS)": 0.75,
    "Branded": 0.45,
}

STATE_KEYWORDS = {
    "raw": ("raw",),
    "cooked": ("cooked", "boiled", "prepared"),
    "boiled": ("boiled",),
    "fried": ("fried",),
    "baked": ("baked",),
    "grilled": ("grilled",),
    "roasted": ("roasted",),
    "dry": ("dry", "uncooked"),
    "canned": ("canned",),
    "smoked": ("smoked",),
}


def _norm(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _text_score(query: str, description: str) -> float:
    q = _norm(query)
    d = _norm(description)
    if not q or not d:
        return 0.0
    if q in d:
        return 1.0
    q_tokens = set(q.split())
    d_tokens = set(d.replace(",", " ").split())
    token_score = len(q_tokens & d_tokens) / max(len(q_tokens), 1)
    ratio = SequenceMatcher(None, q, d).ratio()
    return max(token_score, ratio)


def _data_type_score(data_type: str | None) -> float:
    return DATA_TYPE_SCORES.get(data_type or "", 0.3)


def _state_score(state: str, description: str) -> float:
    if state == "unknown":
        return 0.5
    desc = _norm(description)
    keywords = STATE_KEYWORDS.get(state, ())
    if any(keyword in desc for keyword in keywords):
        return 1.0
    if state in ("cooked", "boiled", "fried", "baked", "grilled", "roasted") and any(
        bad in desc for bad in (" raw", " dry", " uncooked")
    ):
        return 0.0
    return 0.45


def _is_generic_query(query: str) -> bool:
    return len(_norm(query).split()) <= 2


def _penalty(query: str, state: str, description: str, data_type: str | None) -> float:
    desc = _norm(description)
    penalty = 0.0
    if state in ("cooked", "boiled", "fried", "baked", "grilled", "roasted") and any(
        bad in desc for bad in (" raw", " dry", " uncooked")
    ):
        penalty += 0.25
    if _is_generic_query(query) and data_type == "Branded":
        penalty += 0.2
    if "babyfood" in desc or "baby food" in desc:
        penalty += 0.25
    if is_beverage_like_query(query) and ("powder" in desc or "dry mix" in desc) and "powder" not in _norm(query):
        penalty += 0.25
    return penalty


def _scaled_nutrients(per_100g: dict[str, float], grams: int) -> dict[str, float]:
    return {key: round(float(value) * grams / 100.0, 3) for key, value in per_100g.items()}


def _raw_payload_for(ingredients: dict[str, Any] | None, input_name: str) -> dict | None:
    if not ingredients:
        return None
    payload = ingredients.get(input_name)
    return payload if isinstance(payload, dict) else None


class UsdaFoodMatcher:
    def __init__(self, client: UsdaFoodDataClient | None = None):
        self.client = client or UsdaFoodDataClient()
        self.aliases = FoodAliasIndex(None)

    def _build_query(self, ni: NormalizedIngredient, raw_payload: dict | None = None) -> str:
        raw_query = raw_payload.get("usda_search_query") if isinstance(raw_payload, dict) else None
        if isinstance(raw_query, str) and raw_query.strip():
            return raw_query.strip()
        if ni.state and ni.state != "unknown":
            return f"{ni.canonical_query} {ni.state}".strip()
        return ni.canonical_query or ni.input_name

    def match_ingredient(self, ni: NormalizedIngredient, raw_payload: dict | None = None) -> UsdaMatchResult:
        query = self._build_query(ni, raw_payload)
        empty = UsdaMatchResult(
            input_name=ni.input_name,
            query=query,
            grams=ni.grams,
            state=ni.state,
            selected_fdc_id=None,
            selected_description=None,
            selected_data_type=None,
            match_score=0.0,
            match_status="not_found",
            nutrients_per_100g={},
            nutrients_scaled={},
            candidates=[],
        )
        try:
            search = self.client.search_foods(query, page_size=10)
        except UsdaApiError:
            raise
        except Exception as exc:
            raise UsdaApiError("USDA food search failed") from exc

        foods = search.get("foods") if isinstance(search, dict) else None
        if not isinstance(foods, list) or not foods:
            if query != ni.canonical_query and ni.canonical_query:
                try:
                    search = self.client.search_foods(ni.canonical_query, page_size=10)
                    foods = search.get("foods") if isinstance(search, dict) else None
                    query = ni.canonical_query
                except Exception:
                    foods = []
        if not isinstance(foods, list) or not foods:
            return empty

        scored: list[tuple[float, dict]] = []
        candidates: list[dict] = []
        for food in foods:
            if not isinstance(food, dict):
                continue
            description = str(food.get("description") or "")
            data_type = food.get("dataType")
            text = _text_score(query, description)
            dtype = _data_type_score(data_type if isinstance(data_type, str) else None)
            state = _state_score(ni.state, description)
            score = max(0.0, min(1.0, text * 0.55 + dtype * 0.25 + state * 0.20 - _penalty(query, ni.state, description, data_type)))
            candidate = {
                "fdc_id": food.get("fdcId"),
                "description": description,
                "data_type": data_type,
                "match_score": round(score, 3),
            }
            candidates.append(candidate)
            scored.append((score, food))

        if not scored:
            return empty
        score, selected = max(scored, key=lambda item: item[0])
        fdc_id = selected.get("fdcId")
        description = str(selected.get("description") or "")
        data_type = selected.get("dataType")
        details = selected
        if fdc_id:
            try:
                details = self.client.get_food(int(fdc_id))
            except UsdaApiError:
                raise
            except Exception as exc:
                logger.warning("USDA food detail failed for %s: %s", fdc_id, exc)
        per_100g = normalize_usda_food_nutrients(details)
        if not per_100g:
            per_100g = normalize_usda_food_nutrients(selected)

        return UsdaMatchResult(
            input_name=ni.input_name,
            query=query,
            grams=ni.grams,
            state=ni.state,
            selected_fdc_id=int(fdc_id) if fdc_id is not None else None,
            selected_description=description or None,
            selected_data_type=data_type if isinstance(data_type, str) else None,
            match_score=round(score, 3),
            match_status="matched" if per_100g else "no_nutrients",
            nutrients_per_100g=per_100g,
            nutrients_scaled=_scaled_nutrients(per_100g, ni.grams),
            candidates=candidates,
        )

    def parse_ingredients(self, ingredients: dict[str, Any] | None) -> list[NormalizedIngredient]:
        return parse_ingredients_dict(ingredients, self.aliases)

    def raw_payload_for(self, ingredients: dict[str, Any] | None, input_name: str) -> dict | None:
        return _raw_payload_for(ingredients, input_name)
