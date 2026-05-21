"""Category detection for nutrition matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class NutritionCategory(str, Enum):
    MEAT = "meat"
    BEEF = "beef"
    BEEF_PATTY = "beef_patty"
    GROUND_BEEF = "ground_beef"
    BURGER = "burger"
    POULTRY = "poultry"
    SEAFOOD = "seafood"
    FISH = "fish"
    TUNA = "tuna"
    SHRIMP = "shrimp"
    GRAIN = "grain"
    GENERIC_GRAIN = "generic_grain"
    LEGUME = "legume"
    VEGETABLE = "vegetable"
    CORN = "corn"
    FRUIT = "fruit"
    BANANA = "banana"
    DAIRY = "dairy"
    COTTAGE_CHEESE = "cottage_cheese"
    CHEESE = "cheese"
    EGG = "egg"
    SEED = "seed"
    NUT = "nut"
    BEVERAGE = "beverage"
    TEA = "tea"
    COFFEE = "coffee"
    ALCOHOLIC_BEVERAGE = "alcoholic_beverage"
    BEER = "beer"
    SWEET = "sweet"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IngredientCategoryInfo:
    primary: NutritionCategory
    all_categories: frozenset[NutritionCategory]
    reasons: tuple[str, ...] = ()


_GENERIC_GRAIN_TERMS = (
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

_SPECIFIC_GRAIN_TERMS = (
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


def _norm(*parts: str | None) -> str:
    return " ".join(p.strip().lower() for p in parts if isinstance(p, str) and p.strip())


def detect_ingredient_categories(
    input_name: str,
    canonical_query: str,
    alias_category: str | None,
) -> IngredientCategoryInfo:
    blob = _norm(input_name, canonical_query)
    reasons: list[str] = []
    cats: set[NutritionCategory] = set()
    primary = NutritionCategory.UNKNOWN

    def mark(primary_cat: NutritionCategory, *extra: NutritionCategory, reason: str) -> None:
        nonlocal primary
        if primary == NutritionCategory.UNKNOWN:
            primary = primary_cat
        cats.add(primary_cat)
        cats.update(extra)
        reasons.append(reason)

    ac = (alias_category or "").strip().lower()

    # Most specific first.
    if "beer" in blob or "пиво" in blob or ac == "alcoholic_beverage":
        if not any(x in blob for x in ("beer bread", "beer batter", "beer cheese")):
            mark(
                NutritionCategory.BEER,
                NutritionCategory.BEVERAGE,
                NutritionCategory.ALCOHOLIC_BEVERAGE,
                reason="beer_like",
            )
    if "tuna" in blob or "тунец" in blob:
        mark(NutritionCategory.TUNA, NutritionCategory.SEAFOOD, NutritionCategory.FISH, reason="tuna_like")
    if any(
        x in blob
        for x in (
            "smoked fish",
            "kippered",
            "копченая рыба",
            "копчёная рыба",
            "копченый рыб",
            "копчёный рыб",
            "рыба копченая",
            "рыба копчёная",
        )
    ) or (
        ("smoked" in blob or "копчен" in blob or "копчё" in blob)
        and ("fish" in blob or "рыба" in blob or "рыб" in blob)
    ):
        mark(NutritionCategory.FISH, reason="smoked_fish_like")
    if re.search(r"\b(shrimp|shrimps|prawn|prawns)\b", blob) or "кревет" in blob:
        mark(NutritionCategory.SHRIMP, NutritionCategory.SEAFOOD, reason="shrimp_like")
    if "banana" in blob or "банан" in blob:
        mark(NutritionCategory.BANANA, NutritionCategory.FRUIT, reason="banana_like")
    if ac == "cottage_cheese" or "cottage cheese" in blob or "творог" in blob:
        mark(NutritionCategory.COTTAGE_CHEESE, NutritionCategory.DAIRY, reason="cottage_cheese_like")
    if "tea" in blob or "чай" in blob:
        mark(NutritionCategory.TEA, NutritionCategory.BEVERAGE, reason="tea_like")
    if "coffee" in blob or "кофе" in blob:
        mark(NutritionCategory.COFFEE, NutritionCategory.BEVERAGE, reason="coffee_like")
    if (
        "beef patty" in blob
        or "hamburger patty" in blob
        or "burger patty" in blob
        or "котлета для бургера" in blob
        or "бургерная котлета" in blob
        or "говяжья котлета" in blob
        or "котлета из говядины" in blob
        or ac == "beef_patty"
    ):
        mark(
            NutritionCategory.BEEF_PATTY,
            NutritionCategory.BEEF,
            NutritionCategory.MEAT,
            reason="beef_patty_like",
        )
    if (
        "ground beef" in blob
        or "beef mince" in blob
        or "minced beef" in blob
        or "говяжий фарш" in blob
        or "фарш говяжий" in blob
        or "фарш" in blob
        or ac == "ground_beef"
    ):
        mark(
            NutritionCategory.GROUND_BEEF,
            NutritionCategory.BEEF,
            NutritionCategory.MEAT,
            reason="ground_beef_like",
        )
    if (
        "burger" in blob
        or "hamburger" in blob
        or "cheeseburger" in blob
        or ac == "burger"
    ):
        mark(NutritionCategory.BURGER, reason="burger_like")
    if "beef" in blob or "говядин" in blob or ac == "beef":
        mark(NutritionCategory.BEEF, NutritionCategory.MEAT, reason="beef_like")
    if any(x in blob for x in ("chicken", "turkey", "куриц", "индей")) or ac == "poultry":
        mark(NutritionCategory.POULTRY, NutritionCategory.MEAT, reason="poultry_like")
    if re.search(r"\b(corn|sweet corn)\b", blob) or "кукуруз" in blob:
        mark(NutritionCategory.CORN, NutritionCategory.VEGETABLE, reason="corn_like")
    if any(x in blob for x in _GENERIC_GRAIN_TERMS) and not any(x in blob for x in _SPECIFIC_GRAIN_TERMS):
        mark(NutritionCategory.GENERIC_GRAIN, NutritionCategory.GRAIN, reason="generic_grain_like")

    # Alias categories.
    alias_map = {
        "meat": (NutritionCategory.MEAT,),
        "beef": (NutritionCategory.BEEF, NutritionCategory.MEAT),
        "beef_patty": (
            NutritionCategory.BEEF_PATTY,
            NutritionCategory.BEEF,
            NutritionCategory.MEAT,
        ),
        "ground_beef": (
            NutritionCategory.GROUND_BEEF,
            NutritionCategory.BEEF,
            NutritionCategory.MEAT,
        ),
        "burger": (NutritionCategory.BURGER,),
        "poultry": (NutritionCategory.POULTRY, NutritionCategory.MEAT),
        "seafood": (NutritionCategory.SEAFOOD,),
        "fish": (NutritionCategory.FISH,),
        "tuna": (NutritionCategory.TUNA, NutritionCategory.SEAFOOD, NutritionCategory.FISH),
        "grain": (NutritionCategory.GRAIN,),
        "grain_generic_fallback": (NutritionCategory.GENERIC_GRAIN, NutritionCategory.GRAIN),
        "legume": (NutritionCategory.LEGUME,),
        "vegetable": (NutritionCategory.VEGETABLE,),
        "fruit": (NutritionCategory.FRUIT,),
        "berry": (NutritionCategory.FRUIT,),
        "dairy": (NutritionCategory.DAIRY,),
        "cottage_cheese": (NutritionCategory.COTTAGE_CHEESE, NutritionCategory.DAIRY),
        "cheese": (NutritionCategory.CHEESE, NutritionCategory.DAIRY),
        "egg": (NutritionCategory.EGG,),
        "seed": (NutritionCategory.SEED,),
        "seeds": (NutritionCategory.SEED,),
        "nut": (NutritionCategory.NUT,),
        "nuts": (NutritionCategory.NUT,),
        "alcoholic_beverage": (NutritionCategory.ALCOHOLIC_BEVERAGE, NutritionCategory.BEVERAGE),
        "sweet": (NutritionCategory.SWEET,),
    }
    if ac in alias_map:
        vals = alias_map[ac]
        if primary == NutritionCategory.UNKNOWN:
            primary = vals[0]
        cats.update(vals)
        reasons.append(f"alias:{ac}")

    # Generic keyword categories.
    if any(x in blob for x in ("fish", "salmon", "tuna", "тунец", "рыба")):
        cats.add(NutritionCategory.FISH)
    if any(x in blob for x in ("shrimp", "prawn", "кревет")):
        cats.add(NutritionCategory.SEAFOOD)
    if any(x in blob for x in ("rice", "buckwheat", "oat", "quinoa", "bulgur", "couscous", "barley", "spaghetti", "macaroni", "pasta")):
        cats.add(NutritionCategory.GRAIN)
    if re.search(r"\b(beans?|peas?|lentils?|chickpeas?|garbanzos?|kidney beans?)\b", blob) or "фасол" in blob:
        cats.add(NutritionCategory.LEGUME)
    if any(x in blob for x in ("cucumber", "tomato", "carrot", "corn", "pepper", "lettuce", "parsley", "dill", "кукуруз")):
        cats.add(NutritionCategory.VEGETABLE)
    if any(x in blob for x in ("milk", "yogurt", "cream", "cheese", "сыр", "молок", "йогур")):
        cats.add(NutritionCategory.DAIRY)
    if re.search(r"\begg(s)?\b", blob) or "яйц" in blob:
        cats.add(NutritionCategory.EGG)
    if any(x in blob for x in ("seed", "seeds", "chia", "pumpkin seed", "pepitas", "семеч", "семен")):
        cats.add(NutritionCategory.SEED)
    if any(x in blob for x in ("almond", "pecan", "walnut", "cashew", "nut", "nuts", "миндал", "орех")):
        cats.add(NutritionCategory.NUT)
    if any(x in blob for x in ("tea", "coffee", "juice", "drink", "beverage", "чай", "кофе", "сок", "напит")):
        cats.add(NutritionCategory.BEVERAGE)
    if any(x in blob for x in ("chocolate", "truffle", "dessert", "cookie", "candy", "sweet")):
        cats.add(NutritionCategory.SWEET)

    if not cats:
        cats.add(NutritionCategory.UNKNOWN)
    if primary == NutritionCategory.UNKNOWN:
        # Prefer a sensible generic primary if only generic categories were found.
        for candidate in (
            NutritionCategory.GRAIN,
            NutritionCategory.LEGUME,
            NutritionCategory.VEGETABLE,
            NutritionCategory.FRUIT,
            NutritionCategory.DAIRY,
            NutritionCategory.EGG,
            NutritionCategory.SEED,
            NutritionCategory.NUT,
            NutritionCategory.BEVERAGE,
            NutritionCategory.SWEET,
            NutritionCategory.FISH,
            NutritionCategory.SEAFOOD,
            NutritionCategory.MEAT,
            NutritionCategory.UNKNOWN,
        ):
            if candidate in cats:
                primary = candidate
                break

    return IngredientCategoryInfo(
        primary=primary,
        all_categories=frozenset(cats),
        reasons=tuple(reasons),
    )
