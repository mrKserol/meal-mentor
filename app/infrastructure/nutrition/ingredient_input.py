"""Normalize legacy and structured ingredient payloads for nutrition matching."""

from __future__ import annotations

import logging
import re
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
        if (
            state == "dry"
            and entry
            and "dry" not in canonical.lower()
            and "uncooked" not in canonical.lower()
            and "raw" not in canonical.lower()
        ):
            alt = alias_index.lookup(f"dry {input_name}") or alias_index.lookup(f"{input_name} dry")
            if alt:
                canonical = alt.canonical
                alias_category = alt.category or alias_category
                alias_hit = True

        if state in ("fried", "grilled", "baked", "boiled") and entry and state not in canonical.lower():
            alt = alias_index.lookup(f"{state} {input_name}") or alias_index.lookup(f"{input_name} {state}")
            if alt:
                canonical = alt.canonical
                alias_category = alt.category or alias_category
                alias_hit = True

        if is_dates_like_name(input_name) and state == "raw":
            state = "dry"

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


def is_legume_like_ingredient(ni: NormalizedIngredient) -> bool:
    if ni.alias_category == "legume":
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if re.search(r"\b(beans?|peas?|lentils?|chickpeas?|garbanzos?|фасоль|фасоли)\b", blob):
        return True
    return "legume" in blob


_BEVERAGE_HINTS_EN = (
    "tea",
    "coffee",
    "latte",
    "cappuccino",
    "milk tea",
    "cocoa",
    "juice",
    "drink",
    "beverage",
    "smoothie",
    "espresso",
    "americano",
    "macchiato",
    "mocha",
)
_BEVERAGE_HINTS_RU = ("чай", "кофе", "сок", "напиток", "смузи", "латте", "капучино")


def is_beverage_like_query(name: str) -> bool:
    """True for typical drinks (used to avoid matching dry mixes / powders)."""
    q = " ".join(name.strip().lower().split())
    if not q:
        return False
    for h in _BEVERAGE_HINTS_EN:
        if h in q:
            return True
    for h in _BEVERAGE_HINTS_RU:
        if h in q:
            return True
    return False


_POWDER_EXPLICIT = (
    "powder",
    "dry mix",
    "instant powder",
    "сухой",
    "сухая",
    "порошок",
    "смесь",
    "растворимый",
)


def query_implies_beverage_powder_or_dry_mix(name: str) -> bool:
    """User explicitly asked for powder / dry mix (do not penalize those rows)."""
    q = name.strip().lower()
    return any(x in q for x in _POWDER_EXPLICIT)


def is_dates_like_name(name: str) -> bool:
    n = name.strip().lower()
    return bool(re.search(r"\bdate?s?\b", n)) or "финик" in n


def is_egg_like_name(name: str) -> bool:
    n = name.strip().lower()
    if "egg" in n or "яйц" in n:
        return True
    return False


def is_poultry_breast_query(ni: NormalizedIngredient) -> bool:
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if "wing" in blob or "thigh" in blob or "drumstick" in blob:
        return False
    return any(
        k in blob
        for k in (
            "breast",
            "грудк",
            "филе",
            "fillet",
            "skinless",
            "boneless",
        )
    )
