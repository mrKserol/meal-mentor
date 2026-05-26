"""Category detection for nutrition matching."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class NutritionCategory(str, Enum):
    MEAT = "meat"
    BEEF = "beef"
    BEEF_STEAK = "beef_steak"
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
    SOFT_DRINK = "soft_drink"
    ZERO_SOFT_DRINK = "zero_soft_drink"
    SOUP = "soup"
    PREPARED_SOUP = "prepared_soup"
    PREPARED_DISH = "prepared_dish"
    COCONUT_WATER = "coconut_water"
    COCONUT_MEAT = "coconut_meat"
    COCONUT_MILK = "coconut_milk"
    COCONUT_CREAM = "coconut_cream"
    OIL = "oil"
    AVOCADO = "avocado"
    YOGURT = "yogurt"
    SOY_YOGURT = "soy_yogurt"
    WATER = "water"
    SESAME_SEED = "sesame_seed"
    SESAME_PASTE = "sesame_paste"
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


_ZERO_SOFT_DRINK_MARKERS = (
    "zero",
    "diet",
    "light",
    "lite",
    "sugar free",
    "sugar-free",
    "no sugar",
    "без сахара",
    "зеро",
    "лайт",
    "диет",
    "диетическая",
    "нулев",
)


def _is_soft_drink_blob(blob: str) -> bool:
    if re.search(r"\b(coke|pepsi|sprite|soda|soft drink|carbonated)\b", blob):
        return True
    if re.search(r"\bcoca[\s-]*cola\b", blob) or "coca cola" in blob:
        return True
    if re.search(r"\bcola\b", blob):
        return True
    if "кока" in blob and ("кола" in blob or "cola" in blob):
        return True
    if re.search(r"(?:^|\s)кола(?:\s|$)", blob):
        return True
    return False


def _is_zero_soft_drink_blob(blob: str) -> bool:
    return any(m in blob for m in _ZERO_SOFT_DRINK_MARKERS)


_COCONUT_WATER_TERMS = (
    "coconut water",
    "coconut juice",
    "coconut liquid",
    "fresh coconut water",
    "young coconut water",
    "кокосовая вода",
    "вода кокоса",
    "вода из кокоса",
    "кокосовый сок",
    "сок кокоса",
    "жидкость кокоса",
    "жидкость из кокоса",
    "вода из молодого кокоса",
)


def _is_coconut_water_blob(blob: str) -> bool:
    return any(t in blob for t in _COCONUT_WATER_TERMS)


def _is_coconut_milk_blob(blob: str) -> bool:
    return "coconut milk" in blob or "кокосовое молоко" in blob or "кокосовое молок" in blob


def _is_coconut_cream_blob(blob: str) -> bool:
    return "coconut cream" in blob or "кокосовые сливки" in blob or "кокосовые слив" in blob


def _is_coconut_oil_blob(blob: str) -> bool:
    return "coconut oil" in blob or "кокосовое масло" in blob


def _is_coconut_meat_blob(blob: str) -> bool:
    if _is_coconut_water_blob(blob) or _is_coconut_milk_blob(blob) or _is_coconut_cream_blob(blob):
        return False
    if _is_coconut_oil_blob(blob):
        return False
    if any(
        t in blob
        for t in (
            "coconut meat",
            "raw coconut",
            "coconut flesh",
            "мякоть кокоса",
            "кокосовая мякоть",
        )
    ):
        return True
    if re.search(r"\bcoconut\b", blob) or re.search(r"\bкокос\b", blob):
        return True
    return False


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

    # --- Water: check before anything else (avoid watermelon/coconut water confusion) ---
    if ac == "water" or (
        ("water" in blob or "вода" in blob)
        and not any(x in blob for x in (
            "watermelon", "арбуз",
            "coconut water", "coconut juice", "кокосовая вода", "вода кокоса", "вода из кокоса",
            "water buffalo", "water chestnut", "водяной орех",
            "tonic water", "soda water", "sparkling water",
            "water biscuit", "water cracker", "prepared with water", "cooked with water",
            "with water",
        ))
    ) and (
        ac == "water"
        or any(x in blob for x in ("water, generic", "water, bottled", "tap, water", "drinking, tap", "naya", "perrier", "poland spring", "well, tap"))
        or (ac == "water")
    ):
        # Only trigger if alias category is water OR the canonical/input is clearly water-only
        if ac == "water":
            mark(
                NutritionCategory.WATER,
                NutritionCategory.BEVERAGE,
                reason="water_like",
            )

    # --- Soy yogurt ---
    if ac == "soy_yogurt" or any(x in blob for x in ("soy yogurt", "soya yogurt", "соевый йогурт")):
        mark(
            NutritionCategory.SOY_YOGURT,
            NutritionCategory.YOGURT,
            reason="soy_yogurt_like",
        )
    # --- Plain yogurt ---
    elif ac == "yogurt" or any(x in blob for x in ("yogurt", "yoghurt", "йогурт", "йогур")):
        mark(
            NutritionCategory.YOGURT,
            NutritionCategory.DAIRY,
            reason="yogurt_like",
        )

    # --- Tahini / sesame paste ---
    if ac == "sesame_paste" or any(x in blob for x in ("tahini", "тахини", "кунжутная паста")):
        mark(
            NutritionCategory.SESAME_PASTE,
            NutritionCategory.SEED,
            reason="sesame_paste_like",
        )
    # --- Sesame seeds ---
    elif ac == "sesame_seed" or any(x in blob for x in ("sesame seed", "sesame seeds", "кунжут", "семена кунжута")):
        mark(
            NutritionCategory.SESAME_SEED,
            NutritionCategory.SEED,
            reason="sesame_seed_like",
        )

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

    # Avocado oil must be checked BEFORE plain avocado
    if ac == "oil" and ("avocado" in blob or "авокадо" in blob):
        mark(NutritionCategory.OIL, reason="avocado_oil_alias")
    elif any(x in blob for x in ("avocado oil", "масло авокадо", "авокадовое масло")):
        mark(NutritionCategory.OIL, reason="avocado_oil_like")
    elif ac == "avocado" or (
        ("avocado" in blob or "авокадо" in blob)
        and not any(x in blob for x in ("oil", "масло"))
    ):
        mark(NutritionCategory.AVOCADO, NutritionCategory.FRUIT, reason="avocado_like")

    if ac == "coconut_water" or _is_coconut_water_blob(blob):
        mark(
            NutritionCategory.COCONUT_WATER,
            NutritionCategory.BEVERAGE,
            reason="coconut_water_like",
        )
    elif ac == "coconut_milk" or _is_coconut_milk_blob(blob):
        mark(
            NutritionCategory.COCONUT_MILK,
            NutritionCategory.BEVERAGE,
            NutritionCategory.DAIRY,
            reason="coconut_milk_like",
        )
    elif ac == "coconut_cream" or _is_coconut_cream_blob(blob):
        mark(
            NutritionCategory.COCONUT_CREAM,
            NutritionCategory.DAIRY,
            reason="coconut_cream_like",
        )
    elif ac == "oil" or _is_coconut_oil_blob(blob):
        mark(NutritionCategory.OIL, reason="coconut_oil_like")
    elif ac == "coconut_meat" or _is_coconut_meat_blob(blob):
        mark(NutritionCategory.COCONUT_MEAT, NutritionCategory.NUT, reason="coconut_meat_like")

    if ac == "zero_soft_drink":
        mark(
            NutritionCategory.ZERO_SOFT_DRINK,
            NutritionCategory.SOFT_DRINK,
            NutritionCategory.BEVERAGE,
            reason="alias_zero_soft_drink",
        )
    elif ac == "soft_drink":
        mark(
            NutritionCategory.SOFT_DRINK,
            NutritionCategory.BEVERAGE,
            reason="alias_soft_drink",
        )
    elif _is_soft_drink_blob(blob):
        mark(
            NutritionCategory.SOFT_DRINK,
            NutritionCategory.BEVERAGE,
            reason="soft_drink_like",
        )
        if _is_zero_soft_drink_blob(blob):
            mark(
                NutritionCategory.ZERO_SOFT_DRINK,
                NutritionCategory.SOFT_DRINK,
                NutritionCategory.BEVERAGE,
                reason="zero_soft_drink_like",
            )

    _SOUP_TERMS_EN = (
        "soup",
        "borscht",
        "borsch",
        "beet soup",
        "beetroot soup",
        "cabbage soup",
        "tomato soup",
        "lentil soup",
        "bean soup",
        "chicken soup",
        "beef soup",
        "vegetable soup",
        "broth",
        "chowder",
        "kharcho",
        "rassolnik",
        "solyanka",
    )
    _SOUP_TERMS_RU = (
        "суп",
        "борщ",
        "щи",
        "харчо",
        "рассольник",
        "солянка",
        "похлебка",
        "похлёбка",
        "бульон",
        "чечевичный суп",
        "фасолевый суп",
        "томатный суп",
        "овощной суп",
        "куриный суп",
        "грибной суп",
        "капустный суп",
    )
    if ac == "soup" or ac == "prepared_soup" or ac == "prepared_dish":
        mark(
            NutritionCategory.SOUP,
            NutritionCategory.PREPARED_SOUP,
            NutritionCategory.PREPARED_DISH,
            reason="alias_soup",
        )
    elif any(t in blob for t in _SOUP_TERMS_EN + _SOUP_TERMS_RU):
        mark(
            NutritionCategory.SOUP,
            NutritionCategory.PREPARED_SOUP,
            NutritionCategory.PREPARED_DISH,
            reason="soup_like",
        )
        if any(t in blob for t in ("lentil soup", "чечевичный суп", "суп чечевичный")):
            cats.add(NutritionCategory.LEGUME)
        if any(t in blob for t in ("bean soup", "фасолевый суп", "суп фасолевый")):
            cats.add(NutritionCategory.LEGUME)
        if any(
            t in blob
            for t in ("chicken soup", "куриный суп", "суп с курицей", "chicken broth")
        ):
            cats.add(NutritionCategory.POULTRY)
            cats.add(NutritionCategory.MEAT)
        if any(t in blob for t in ("beef soup", "kharcho", "харчо", "beef barley")):
            cats.add(NutritionCategory.BEEF)
            cats.add(NutritionCategory.MEAT)
        if any(
            t in blob
            for t in (
                "tomato soup",
                "томатный суп",
                "суп томатный",
                "vegetable soup",
                "овощной суп",
                "cabbage soup",
                "щи",
                "капустный суп",
            )
        ):
            cats.add(NutritionCategory.VEGETABLE)

    # Beef steak — must come before generic beef check, but NOT match tallow/fat
    _BEEF_STEAK_TERMS = (
        "beef steak",
        "grilled beef steak",
        "grilled steak",
        "broiled steak",
        "cooked steak",
        "говяжий стейк",
        "стейк говяжий",
        "стейк из говядины",
        "жареный стейк",
        "стейк на гриле",
        "sirloin steak",
        "ribeye steak",
        "ribeye",
        "rib eye",
        "tenderloin steak",
        "t-bone steak",
        "strip steak",
        "новый йорк",
    )
    _is_steak_blob = (
        ac == "beef_steak"
        or any(t in blob for t in _BEEF_STEAK_TERMS)
        or (re.search(r"\bsteak\b", blob) and not any(x in blob for x in ("tallow", "beef fat", "separable fat", "fat only", "suet", "lard", "oil")))
    )
    if _is_steak_blob and not any(x in blob for x in ("tallow", "beef fat", "separable fat", "fat only", "suet", "lard")):
        mark(
            NutritionCategory.BEEF_STEAK,
            NutritionCategory.BEEF,
            NutritionCategory.MEAT,
            reason="beef_steak_like",
        )

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
        "beef_steak": (NutritionCategory.BEEF_STEAK, NutritionCategory.BEEF, NutritionCategory.MEAT),
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
        "soup": (
            NutritionCategory.SOUP,
            NutritionCategory.PREPARED_SOUP,
            NutritionCategory.PREPARED_DISH,
        ),
        "prepared_soup": (
            NutritionCategory.SOUP,
            NutritionCategory.PREPARED_SOUP,
            NutritionCategory.PREPARED_DISH,
        ),
        "prepared_dish": (NutritionCategory.PREPARED_DISH,),
        "soft_drink": (NutritionCategory.SOFT_DRINK, NutritionCategory.BEVERAGE),
        "zero_soft_drink": (
            NutritionCategory.ZERO_SOFT_DRINK,
            NutritionCategory.SOFT_DRINK,
            NutritionCategory.BEVERAGE,
        ),
        "coconut_water": (NutritionCategory.COCONUT_WATER, NutritionCategory.BEVERAGE),
        "coconut_meat": (NutritionCategory.COCONUT_MEAT, NutritionCategory.NUT),
        "coconut_milk": (NutritionCategory.COCONUT_MILK, NutritionCategory.BEVERAGE),
        "coconut_cream": (NutritionCategory.COCONUT_CREAM, NutritionCategory.DAIRY),
        "oil": (NutritionCategory.OIL,),
        "avocado": (NutritionCategory.AVOCADO, NutritionCategory.FRUIT),
        "yogurt": (NutritionCategory.YOGURT, NutritionCategory.DAIRY),
        "soy_yogurt": (NutritionCategory.SOY_YOGURT, NutritionCategory.YOGURT),
        "water": (NutritionCategory.WATER, NutritionCategory.BEVERAGE),
        "sesame_seed": (NutritionCategory.SESAME_SEED, NutritionCategory.SEED),
        "sesame_paste": (NutritionCategory.SESAME_PASTE, NutritionCategory.SEED),
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
    if not re.search(r"\bcoconut\b", blob) and not re.search(r"\bкокос\b", blob):
        if any(x in blob for x in ("almond", "pecan", "walnut", "cashew", "миндал", "орех")):
            cats.add(NutritionCategory.NUT)
        elif re.search(r"\b(nut|nuts)\b", blob):
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
            NutritionCategory.WATER,
            NutritionCategory.SOY_YOGURT,
            NutritionCategory.YOGURT,
            NutritionCategory.SESAME_SEED,
            NutritionCategory.SESAME_PASTE,
            NutritionCategory.COCONUT_WATER,
            NutritionCategory.COCONUT_MILK,
            NutritionCategory.COCONUT_CREAM,
            NutritionCategory.COCONUT_MEAT,
            NutritionCategory.AVOCADO,
            NutritionCategory.OIL,
            NutritionCategory.ZERO_SOFT_DRINK,
            NutritionCategory.SOFT_DRINK,
            NutritionCategory.SOUP,
            NutritionCategory.PREPARED_SOUP,
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
            NutritionCategory.BEEF_STEAK,
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
