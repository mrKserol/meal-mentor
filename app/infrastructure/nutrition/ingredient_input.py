"""Normalize legacy and structured ingredient payloads for nutrition matching."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.infrastructure.nutrition.food_aliases import AliasEntry, FoodAliasIndex
from app.infrastructure.nutrition.nutrition_categories import (
    IngredientCategoryInfo,
    NutritionCategory,
    detect_ingredient_categories,
)

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
        "smoked",
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
    category_primary: str
    categories: tuple[str, ...]
    category_reasons: tuple[str, ...]


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
        state = infer_state_for_porridge_query(input_name, state)
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

        cat_info = detect_ingredient_categories(input_name, canonical, alias_category)

        out.append(
            NormalizedIngredient(
                input_name=input_name,
                canonical_query=canonical,
                grams=grams,
                state=state,
                alias_hit=alias_hit,
                alias_category=alias_category,
                category_primary=cat_info.primary.value,
                categories=tuple(sorted(c.value for c in cat_info.all_categories)),
                category_reasons=cat_info.reasons,
            )
        )
    return out


def is_grain_like_ingredient(ni: NormalizedIngredient) -> bool:
    if NutritionCategory.GRAIN.value in ni.categories:
        return True
    return _is_grain_like(ni.input_name, ni.alias_category) or _is_grain_like(ni.canonical_query, ni.alias_category)


def is_legume_like_ingredient(ni: NormalizedIngredient) -> bool:
    if NutritionCategory.LEGUME.value in ni.categories:
        return True
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


def is_tea_drink_query(ni: NormalizedIngredient) -> bool:
    """Plain tea / чай (not powder); excludes milk tea phrasing handled separately."""
    if query_implies_beverage_powder_or_dry_mix(ni.input_name):
        return False
    il = ni.input_name.strip().lower()
    if "milk" in il and "tea" in il:
        return False
    if "молок" in il and "чай" in il:
        return False
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if "tea" not in blob and "чай" not in blob:
        return False
    return is_beverage_like_query(ni.input_name)


def is_cottage_cheese_like(ni: NormalizedIngredient) -> bool:
    if NutritionCategory.COTTAGE_CHEESE.value in ni.categories:
        return True
    if ni.alias_category == "cottage_cheese":
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if "творог" in blob:
        return True
    if re.search(r"\bcottage\s+cheese\b", blob):
        return True
    if "cottage" in blob and "cheese" in blob:
        return True
    if re.search(r"\bcurd\b", blob) and "cheesecake" not in blob:
        return True
    return False


def is_banana_fruit_like(ni: NormalizedIngredient) -> bool:
    if NutritionCategory.BANANA.value in ni.categories:
        return True
    if ni.alias_category == "fruit" and "banana" in ni.canonical_query.lower():
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if re.search(r"\b(bananas?|бананы?|банан)\b", blob):
        return True
    return False


def is_seed_kernel_query(ni: NormalizedIngredient) -> bool:
    if NutritionCategory.SEED.value in ni.categories:
        return True
    if ni.alias_category in ("seed", "seeds"):
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if "chia" in blob:
        return True
    if "pumpkin seed" in blob or "pepitas" in blob:
        return True
    if "тыкв" in blob and ("семеч" in blob or "семен" in blob):
        return True
    if "тыквенные" in blob:
        return True
    return False


def is_fish_like_ingredient(ni: NormalizedIngredient) -> bool:
    """Plain fish queries (not tuna-in-oil, not shrimp/prawn)."""
    if is_tuna_like_ingredient(ni):
        return False
    if is_seafood_like_ingredient(ni):
        return False
    if NutritionCategory.FISH.value in ni.categories:
        return True
    if ni.alias_category == "fish":
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if "fish oil" in blob or "рыбий жир" in blob or "рыбьего жира" in blob:
        return False
    fish_words = (
        "fish",
        "рыба",
        "рыб",
        "salmon",
        "herring",
        "mackerel",
        "trout",
        "cod",
        "whitefish",
        "sardine",
        "haddock",
        "sablefish",
        "cisco",
        "kippered",
        "losos",
        "лосос",
        "сельд",
        "скумбр",
        "форел",
        "треск",
        "судак",
    )
    return any(w in blob for w in fish_words)


def is_smoked_fish_like_ingredient(ni: NormalizedIngredient) -> bool:
    if not is_fish_like_ingredient(ni):
        return False
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    smoked = (
        "smoked",
        "kippered",
        "lox",
        "копчен",
        "копчё",
        "копченая",
        "копчёная",
        "копченый",
        "копчёный",
    )
    return any(s in blob for s in smoked)


def is_tuna_like_ingredient(ni: NormalizedIngredient) -> bool:
    """True for canned/fresh tuna queries (not generic fish)."""
    if NutritionCategory.TUNA.value in ni.categories:
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if "тунец" in blob or "тунца" in blob or "тунцом" in blob:
        return True
    if "tuna" in blob:
        return True
    if ni.alias_category == "fish" and "tuna" in ni.canonical_query.lower():
        return True
    return False


def is_seafood_like_ingredient(ni: NormalizedIngredient) -> bool:
    """True for seafood-like queries (shrimp/prawn in EN/RU)."""
    if NutritionCategory.SEAFOOD.value in ni.categories or NutritionCategory.SHRIMP.value in ni.categories:
        return True
    if ni.alias_category == "seafood":
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if re.search(r"\b(shrimp|shrimps|prawn|prawns)\b", blob):
        return True
    if re.search(r"\b(креветк[аеи]|креветка|креветки)\b", blob):
        return True
    return False


def is_corn_like_ingredient(ni: NormalizedIngredient) -> bool:
    """True for plain corn / sweet corn queries (not flour/starch/popcorn/snacks)."""
    if NutritionCategory.CORN.value in ni.categories:
        return True
    if ni.alias_category == "vegetable" and "corn" in ni.canonical_query.lower():
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if "corn" not in blob and "кукуруз" not in blob:
        return False
    bad = ("cornmeal", "flour", "starch", "cereal", "snacks", "chips", "popcorn", "tortilla", "bread")
    if any(b in blob for b in bad):
        return False
    if any(x in blob for x in ("corn", "sweet corn", "кукуруз")):
        return True
    return False


def is_beer_like_ingredient(ni: NormalizedIngredient) -> bool:
    """
    True for beer/alcoholic-beverage queries (beer/lager/ale, пиво),
    but excludes food derivatives like beer bread/batter/cheese.
    """
    if NutritionCategory.BEER.value in ni.categories:
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if ni.alias_category == "alcoholic_beverage":
        pass
    elif not any(x in blob for x in ("beer", "lager", "ale", "пиво", "alcoholic beverage")):
        return False
    bad = ("beer bread", "beer batter", "beer cheese")
    if any(x in blob for x in bad):
        return False
    return True


def is_generic_grain_query(ni: NormalizedIngredient) -> bool:
    """Detect vague grain queries ('cooked grains') but ignore specific grain names."""
    if NutritionCategory.GENERIC_GRAIN.value in ni.categories:
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    specific = (
        "buckwheat",
        "rice",
        "oat",
        "oats",
        "oat groats",
        "oatmeal",
        "barley",
        "quinoa",
        "bulgur",
        "couscous",
        "pasta",
        "spaghetti",
        "macaroni",
        "millet",
        "греч",
        "рис",
        "овес",
        "овёс",
        "овсян",
        "перлов",
        "киноа",
        "булгур",
        "кускус",
        "макарон",
        "пшено",
    )
    if any(s in blob for s in specific):
        return False
    generic = (
        "grains",
        "cooked grains",
        "mixed grains",
        "cereals",
        "cereal grains",
        "grain mix",
        "злаки",
        "зерна",
        "зёрна",
        "крупа",
        "смесь круп",
        "вареные злаки",
        "варёные злаки",
    )
    return any(g in blob for g in generic)


def is_beef_like_ingredient(ni: NormalizedIngredient) -> bool:
    if NutritionCategory.BEEF.value in ni.categories:
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    return "beef" in blob or "говядин" in blob


def is_beef_patty_like_ingredient(ni: NormalizedIngredient) -> bool:
    if NutritionCategory.BEEF_PATTY.value in ni.categories:
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    keys = (
        "beef patty",
        "hamburger patty",
        "burger patty",
        "котлета для бургера",
        "бургерная котлета",
        "говяжья котлета",
        "котлета из говядины",
    )
    return any(k in blob for k in keys)


def is_porridge_like_query(name: str) -> bool:
    """True for cooked porridge-like grain names (before normalization)."""
    blob = name.lower()
    if any(x in blob for x in ("dry", "flour", "мука", "сухая", "сухой", "uncooked", "unprepared")):
        return False
    keys = (
        "porridge",
        "polenta",
        "grits",
        "mush",
        "cooked cereal",
        "каша",
        "мамалыга",
        "полента",
        "cornmeal porridge",
        "corn porridge",
        "кукурузная каша",
        "millet porridge",
        "пшенная каша",
        "пшено",
        "buckwheat porridge",
        "rice porridge",
        "oatmeal",
    )
    return any(k in blob for k in keys)


def infer_state_for_porridge_query(input_name: str, state: str) -> str:
    """Plain-weight recalc must still treat porridge as cooked, not dry grain."""
    if state != "unknown":
        return state
    if is_porridge_like_query(input_name):
        return "cooked"
    return state


def is_porridge_like_grain(ni: NormalizedIngredient) -> bool:
    """True for cooked porridge-like grain queries (cornmeal porridge/polenta/grits/mush/каша)."""
    if is_porridge_like_query(ni.input_name) or is_porridge_like_query(ni.canonical_query):
        return True
    blob = f"{ni.input_name} {ni.canonical_query}".lower()
    if any(x in blob for x in ("dry", "flour", "мука", "сухая", "сухой")):
        return False
    keys = (
        "porridge",
        "polenta",
        "grits",
        "mush",
        "cooked cereal",
        "каша",
        "мамалыга",
        "полента",
        "cornmeal porridge",
        "corn porridge",
        "кукурузная каша",
        "millet porridge",
        "пшенная каша",
    )
    return any(k in blob for k in keys)


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
