"""Normalize legacy and structured ingredient payloads for nutrition matching."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.infrastructure.nutrition.food_aliases import AliasEntry, FoodAliasIndex

logger = logging.getLogger(__name__)

ALLOWED_STATES = frozenset(
    {
        "raw",
        "cooked",
        "boiled",
        "fried",
        "baked",
        "grilled",
        "roasted",
        "dry",
        "canned",
        "unknown",
    }
)


@dataclass(frozen=True)
class NormalizedIngredient:
    input_name: str
    canonical_query: str
    grams: int
    state: str
    alias_hit: bool
    alias_category: str | None


def _coerce_grams(val: Any) -> int | None:
    if val is None:
        return None
    try:
        g = int(round(float(val)))
    except (TypeError, ValueError):
        return None
    return g


def _coerce_state(val: Any) -> str:
    if not isinstance(val, str):
        return "unknown"
    s = val.strip().lower()
    return s if s in ALLOWED_STATES else "unknown"


def _is_grain_like(name: str, category: str | None) -> bool:
    if category == "grain":
        return True
    n = name.lower()
    keys = (
        "buckwheat",
        "rice",
        "pasta",
        "noodle",
        "spaghetti",
        "macaroni",
        "couscous",
        "bulgur",
        "quinoa",
        "oat",
        "barley",
        "millet",
        "groats",
        "lentil",
        "bean",
        "chickpea",
        "pea,",
        "peas",
        "semolina",
        "flour",
        "wheat",
        "cornmeal",
        "polenta",
    )
    return any(k in n for k in keys)


def parse_ingredients_dict(
    ingredients: dict[str, Any] | None,
    aliases: FoodAliasIndex | None,
) -> list[NormalizedIngredient]:
    """
    Legacy: {"rice": 120}
    New: {"rice": {"grams": 120, "state": "cooked"}}
    """
    if not ingredients or not isinstance(ingredients, dict):
        return []
    alias_index = aliases or FoodAliasIndex(None)
    out: list[NormalizedIngredient] = []
    for raw_name, payload in ingredients.items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        input_name = raw_name.strip()
        grams: int | None = None
        state = "unknown"
        if isinstance(payload, (int, float)):
            grams = _coerce_grams(payload)
        elif isinstance(payload, dict):
            grams = _coerce_grams(payload.get("grams"))
            state = _coerce_state(payload.get("state"))
        else:
            grams = _coerce_grams(payload)
        if grams is None or grams < 0:
            logger.warning("Skipping ingredient %r: invalid grams %r", input_name, payload)
            continue
        if grams == 0:
            logger.warning("Skipping ingredient %r: zero grams", input_name)
            continue

        entry: AliasEntry | None = alias_index.lookup(input_name)
        alias_hit = entry is not None
        canonical = entry.canonical if entry else input_name
        alias_category = entry.category if entry else None
        if state == "unknown" and entry and entry.default_state and entry.default_state != "unknown":
            state = entry.default_state

        out.append(
            NormalizedIngredient(
                input_name=input_name,
                canonical_query=canonical,
                grams=grams,
                state=state,
                alias_hit=alias_hit,
                alias_category=alias_category,
            )
        )
    return out


def is_grain_like_ingredient(ni: NormalizedIngredient) -> bool:
    return _is_grain_like(ni.input_name, ni.alias_category) or _is_grain_like(ni.canonical_query, ni.alias_category)
