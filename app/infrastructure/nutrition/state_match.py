"""Infer preparation hints from USDA-style names and score vs requested state."""

from __future__ import annotations

import re
from typing import Iterable

from app.infrastructure.nutrition.ingredient_input import (
    is_beverage_like_query,
    is_egg_like_name,
    query_implies_beverage_powder_or_dry_mix,
)


def infer_states_from_candidate_name(candidate_name: str) -> set[str]:
    """Heuristic tags implied by the nutrition.csv description."""
    n = candidate_name.lower()
    out: set[str] = set()
    if re.search(r"\braw\b", n) or ", raw" in n or " raw," in n:
        out.add("raw")
    if "uncooked" in n or "unprepared" in n or re.search(r"\bdry\b", n) or "dry mix" in n:
        out.add("dry")
    if "cooked" in n or "cooked," in n or ", cooked" in n:
        out.add("cooked")
    if "boiled" in n or "steamed" in n or "simmered" in n:
        out.add("boiled")
        out.add("cooked")
    if "fried" in n or "pan-fried" in n or "pan fried" in n:
        out.add("fried")
    if "baked" in n:
        out.add("baked")
    if "grilled" in n:
        out.add("grilled")
    if "roasted" in n:
        out.add("roasted")
    if "canned" in n or "drained solids" in n:
        out.add("canned")
    if "flour" in n or "powder" in n or "dry mix" in n:
        out.add("dry")
    if re.search(r"\bfresh\b", n):
        out.add("raw")
    return out


def _has_any(hay: str, needles: Iterable[str]) -> bool:
    h = hay.lower()
    return any(x in h for x in needles)


def _query_implies_flour_powder(query: str) -> bool:
    q = query.lower()
    return any(w in q for w in ("flour", "powder", "mix", "meal", "starch"))


def _word_cooked(n: str) -> bool:
    return bool(re.search(r"\bcooked\b", n))


def _poultry_breast_bad_match(n: str) -> float:
    """Penalty when user asked for breast/fillet but candidate is processed / other cut."""
    score = 0.0
    bad = (
        ("skin", -80),
        ("breaded", -85),
        ("patty", -85),
        ("nuggets", -90),
        ("fast food", -90),
        (" wing", -80),
        ("wing,", -80),
        (" thigh", -80),
        ("thigh,", -80),
        ("dark meat", -75),
        ("canned", -70),
        ("spread", -75),
        ("sausage", -80),
        ("honey glazed", -60),
        ("honey-glazed", -60),
        ("deli", -50),
        ("rotisserie seasoned", -45),
        ("batter, fried", -70),
        ("flour, fried", -70),
        ("meat and skin", -55),
    )
    for needle, pen in bad:
        if needle in n:
            score += pen
    return max(score, -220.0)


def _legume_cooked_boiled_extra(n: str, query_lower: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    if "boiled" in n:
        score += 45
        reasons.append("+45:legume_boiled")
    if _word_cooked(n):
        score += 35
        reasons.append("+35:legume_cooked")
    if "canned" in n:
        score += 20
        reasons.append("+20:legume_canned")
    if re.search(r"\braw\b", n) or ", raw" in n:
        score -= 70
        reasons.append("-70:legume_raw")
    if "dry" in n or "uncooked" in n or "unprepared" in n:
        score -= 70
        reasons.append("-70:legume_dry")
    has_prep = "boiled" in n or _word_cooked(n) or "canned" in n
    if "mature seeds" in n and not has_prep:
        score -= 70
        reasons.append("-70:legume_mature_seeds_unprepared")
    if "sprouted" in n and "sprouted" not in query_lower:
        score -= 50
        reasons.append("-50:legume_sprouted")
    return score, reasons


def _beverage_candidate_adjustment(n: str) -> tuple[float, list[str]]:
    """Prefer brewed / tap-water beverages; penalize powders and dry mixes."""
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    if "brewed" in nl or "prepared with tap water" in nl or "prepared with distilled water" in nl:
        score += 45
        reasons.append("+45:beverage_brewed_or_prepared_water")
    penalties: list[tuple[str, str, int]] = [
        ("powder", "beverage_powder", 90),
        ("sweetened powder", "beverage_sweetened_powder", 90),
        ("prepared from powder", "beverage_prepared_from_powder", 90),
        ("dry mix", "beverage_dry_mix", 90),
        ("protein powder", "beverage_protein_powder", 90),
        ("beverage powder", "beverage_powder_label", 90),
        ("milkshake mix", "beverage_milkshake_mix", 90),
        ("instant", "beverage_instant", 85),
        ("cereal", "beverage_cereal", 85),
        ("dessert", "beverage_dessert", 85),
    ]
    for needle, tag, pen in penalties:
        if needle in nl:
            score -= float(pen)
            reasons.append(f"-{pen}:{tag}")
    if re.search(r"milk,\s*dry|nonfat dry milk|dry milk", nl):
        score -= 85
        reasons.append("-85:beverage_dry_milk")
    if re.search(r"\bmix\b", nl) and "brewed" not in nl and "prepared with tap water" not in nl:
        score -= 85
        reasons.append("-85:beverage_mix_non_brewed")
    if re.search(r"\bdry\b", nl) and "brewed" not in nl and "prepared with tap water" not in nl:
        if any(x in nl for x in ("beverage", "drink", "tea", "coffee", "cocoa", "juice")):
            score -= 85
            reasons.append("-85:beverage_dry_drink_product")
    return max(score, -320.0), reasons


def _tea_drink_row_adjustment(n: str, ing_lower: str) -> tuple[float, list[str]]:
    """Avoid teaseed oil / non-tea rows when user asked for a tea drink."""
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    if "teaseed" in nl or "tea seed" in nl:
        score -= 220
        reasons.append("-220:tea_teaseed_oil")
    if nl.startswith("oil,") and "tea" in ing_lower:
        score -= 120
        reasons.append("-120:tea_oil_row")
    if ("brewed" in nl or "prepared with tap water" in nl or "prepared with distilled water" in nl) and (
        ", tea" in nl or ", herb, tea" in nl or nl.endswith(" tea")
    ):
        score += 55
        reasons.append("+55:tea_brewed_row")
    if "tea" in nl and "beverage" in nl and ("brewed" in nl or "prepared with tap water" in nl):
        score += 25
        reasons.append("+25:tea_beverage_brewed")
    return max(score, -280.0), reasons


def _cottage_cheese_adjustment(n: str, query_lower: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    if "cottage-cut" in nl or "cottage cut" in nl:
        score -= 150
        reasons.append("-150:cottage_cut_potato")
    if "cottage" in nl:
        score += 70
        reasons.append("+70:cottage_word")
    if "cheese, cottage" in nl or ("cheese, " in nl and "cottage" in nl):
        score += 40
        reasons.append("+40:cottage_cheese_phrase")
    if ("lowfat" in nl or "creamed" in nl or "nonfat" in nl) and "cottage" in nl:
        score += 20
        reasons.append("+20:cottage_lowfat_or_creamed")

    def q_has(s: str) -> bool:
        return s in query_lower

    for needle, pen in (
        ("cheddar", -100),
        ("cream cheese", -100),
        ("cheese spread", -100),
        ("cheesecake", -100),
        ("dessert", -100),
        ("processed", -80),
        ("pasteurized process", -80),
        ("parmesan", -80),
        ("swiss", -80),
        ("feta", -80),
        ("mozzarella", -80),
    ):
        if needle in nl and not q_has(needle):
            score += float(pen)
            reasons.append(f"{pen:.0f}:cottage_bad_{needle.replace(' ', '_')}")
    if "cottage" not in nl and re.search(r"\bcheese\b", nl):
        score -= 60
        reasons.append("-60:cottage_missing")
    return max(score, -320.0), reasons


def _banana_fruit_adjustment(n: str, query_lower: str, requested_state: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    rs = (requested_state or "unknown").lower()

    if "bananas" in nl and "raw" in nl:
        score += 75
        reasons.append("+75:bananas_raw")
    elif "banana" in nl and "raw" in nl and "pepper" not in nl:
        score += 45
        reasons.append("+45:banana_raw")
    elif "raw" in nl and "banana" in nl:
        score += 30
        reasons.append("+30:banana_raw_soft")

    if "pepper" in nl and "banana" in nl and "pepper" not in query_lower:
        score -= 120
        reasons.append("-120:banana_pepper_confusion")
    if "melon" in nl and "banana" in nl and "navajo" in nl:
        score -= 100
        reasons.append("-100:banana_melon_navajo")

    def qx(*words: str) -> bool:
        return any(w in query_lower for w in words)

    if "babyfood" in nl and not qx("babyfood", "baby"):
        score -= 85
        reasons.append("-85:banana_babyfood")
    for bad, tag in (
        ("juice", "juice"),
        ("beverage", "beverage"),
        ("chips", "chips"),
        ("flour", "flour"),
        ("dessert", "dessert"),
        ("pudding", "pudding"),
        ("cake", "cake"),
    ):
        if bad in nl and not qx(bad):
            score -= 80
            reasons.append(f"-80:banana_{tag}")
    if rs != "dry" and any(x in nl for x in ("dried", "dehydrated", "powder")):
        score -= 85
        reasons.append("-85:banana_not_dry_but_dried_row")
    return max(score, -280.0), reasons


def _seed_kernel_adjustment(n: str, query_lower: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    wants_chia = "chia" in query_lower
    wants_pumpkin_blob = "pumpkin" in query_lower or "тыкв" in query_lower or "pepitas" in query_lower
    wants_pumpkin_seed = wants_pumpkin_blob and (
        "seed" in query_lower
        or "pepitas" in query_lower
        or "семеч" in query_lower
        or "семен" in query_lower
    )

    def qx(*words: str) -> bool:
        return any(w in query_lower for w in words)

    if wants_chia:
        if "chia" in nl:
            score += 70
            reasons.append("+70:chia_word")
        if "dried" in nl or "dry" in nl:
            score += 25
            reasons.append("+25:chia_dried")
        if "pumpkin" in nl and "chia" not in nl:
            score -= 80
            reasons.append("-80:chia_query_pumpkin_row")
    if wants_pumpkin_seed:
        if "pumpkin" in nl:
            score += 60
            reasons.append("+60:pumpkin_seed_word")
        if "seeds" in nl or "seed" in nl:
            score += 45
            reasons.append("+45:seeds_word")
        if "kernels" in nl:
            score += 35
            reasons.append("+35:kernels")
        if "dried" in nl:
            score += 25
            reasons.append("+25:seed_dried")
        if "chia" in nl and "pumpkin" not in nl:
            score -= 70
            reasons.append("-70:pumpkin_query_chia_row")

    for bad, pen in (
        ("fish oil", 100),
        ("babyfood", 85),
        ("flour", 85),
        ("meal", 85),
        ("butter", 85),
        ("beverage", 85),
        ("soup", 85),
        ("sprouts", 85),
    ):
        if bad in nl and not qx(bad):
            score -= float(pen)
            reasons.append(f"-{pen:.0f}:seed_{bad.replace(' ', '_')}")
    if (wants_chia or wants_pumpkin_seed) and nl.startswith("oil,"):
        score -= 110
        reasons.append("-110:seed_query_oil_row")

    return max(score, -300.0), reasons


def _tuna_canned_adjustment(n: str, ing: str, query_lower: str) -> tuple[float, list[str]]:
    """Boost real canned tuna rows; penalize oil, salad, soups, non-tuna fish for canned queries."""
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    blob = f"{ing} {query_lower}".lower()
    wants_oil = any(
        x in blob
        for x in (
            " in oil",
            "in oil",
            "oil pack",
            "масло",
            "tuna in oil",
            "canned tuna in oil",
            "canned in oil",
        )
    )

    if "tuna" in nl:
        score += 60
        reasons.append("+60:tuna_word")
    if "canned" in nl:
        score += 45
        reasons.append("+45:tuna_canned")
    if "drained solids" in nl:
        score += 35
        reasons.append("+35:tuna_drained_solids")
    if "in water" in nl and not wants_oil:
        score += 25
        reasons.append("+25:tuna_in_water")
    if "in oil" in nl and wants_oil:
        score += 25
        reasons.append("+25:tuna_in_oil")
    if "light" in nl or "white" in nl:
        score += 15
        reasons.append("+15:tuna_light_or_white")

    if "fish oil" in nl:
        score -= 100
        reasons.append("-100:tuna_fish_oil")
    if "babyfood" in nl:
        score -= 90
        reasons.append("-90:tuna_babyfood")
    if "salad" in nl and "salad" not in blob and "салат" not in blob:
        score -= 80
        reasons.append("-80:tuna_salad_mismatch")
    for bad, tag in (
        ("soup", "tuna_soup"),
        ("sauce", "tuna_sauce"),
        ("spread", "tuna_spread"),
    ):
        if bad in nl:
            score -= 80
            reasons.append(f"-80:{tag}")
    if re.search(r"\braw\b", nl) or ", raw" in nl:
        score -= 80
        reasons.append("-80:tuna_raw_product")
    if "smoked" in nl:
        score -= 80
        reasons.append("-80:tuna_smoked")
    if re.search(r"\bfresh\b", nl):
        score -= 60
        reasons.append("-60:tuna_fresh")
    if re.search(r"\bdry\b", nl) or "dry heat" in nl:
        score -= 60
        reasons.append("-60:tuna_dry")
    if "roe" in nl:
        score -= 60
        reasons.append("-60:tuna_roe")
    if "tuna" not in nl:
        score -= 60
        reasons.append("-60:not_tuna")

    return max(score, -280.0), reasons


def _shrimp_candidate_adjustment(n: str, query_lower: str, requested_state: str) -> tuple[float, list[str]]:
    """
    Prefer plain shrimp rows; aggressively avoid breaded/tempura/fast-food/dish/sauce.
    This is used for shrimp/prawn-like queries (EN/RU) only.
    """
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    rs = (requested_state or "unknown").lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if "shrimp" in nl:
        add(70, "shrimp_word")
    else:
        add(-70, "missing_shrimp_word")
    if "crustaceans" in nl:
        add(40, "crustaceans")
    if "cooked" in nl:
        add(40, "cooked_word")
    if "moist heat" in nl:
        add(35, "moist_heat")
    if "boiled" in nl or "steamed" in nl:
        add(25, "boiled_or_steamed")
    if "raw" in nl and rs == "raw":
        add(15, "raw_aligned")

    for bad in ("breaded", "battered", "tempura"):
        if bad in nl:
            add(-100, f"bad_{bad}")
    for bad in ("fast food",):
        if bad in nl:
            add(-90, f"bad_{bad.replace(' ', '_')}")
    if "fried" in nl and rs != "fried":
        add(-90, "fried_mismatch")
    for bad in ("sauce", "with sauce", "salad", "soup", "gumbo", "dish", "mixture"):
        if bad in nl and bad not in query_lower:
            add(-80, f"bad_{bad.replace(' ', '_')}")
    if "canned" in nl and rs != "canned":
        add(-70, "canned_mismatch")
    if "dried" in nl or re.search(r"\bdry\b", nl):
        add(-70, "dried_or_dry")

    return max(score, -360.0), reasons


def _corn_candidate_adjustment(n: str, query_lower: str, requested_state: str) -> tuple[float, list[str]]:
    """Prefer plain sweet/whole-kernel corn; avoid starch/flour/cereal/snacks/popcorn/dry rows."""
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    rs = (requested_state or "unknown").lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    wants_plain = not any(w in query_lower for w in ("flour", "meal", "cereal", "starch", "popcorn", "chips"))

    if wants_plain:
        if "corn, sweet" in nl or "sweet corn" in nl:
            add(60, "sweet_corn")
        if "whole kernel" in nl:
            add(20, "whole_kernel")
        if "cooked" in nl or "boiled" in nl or "microwaved" in nl or "steamed" in nl:
            add(35, "cooked_like")
        if "canned" in nl and rs == "canned":
            add(30, "canned_aligned")

        for bad in ("cornmeal", "flour", "starch", "cereal", "snacks", "chips"):
            if bad in nl and bad not in query_lower:
                add(-100, f"bad_{bad}")
        if "popcorn" in nl and "popcorn" not in query_lower:
            add(-90, "bad_popcorn")
        if "dry" in nl and rs != "dry":
            add(-80, "dry_mismatch")
        if "raw" in nl and rs != "raw":
            add(-80, "raw_mismatch")
        if "babyfood" in nl and "baby" not in query_lower and "babyfood" not in query_lower:
            add(-80, "babyfood")
        for bad in ("bread", "tortilla"):
            if bad in nl and bad not in query_lower:
                add(-70, f"bad_{bad}")

    return max(score, -360.0), reasons


def _beer_candidate_adjustment(n: str, query_lower: str) -> tuple[float, list[str]]:
    """Prefer alcoholic beverage beer rows over food/dry/mix/yeast/snack rows."""
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    wants_light = any(x in ql for x in ("light", "легкое", "лёгкое"))
    wants_strong = any(x in ql for x in ("strong", "крепкое", "high alcohol"))

    if "alcoholic beverage" in nl or "alcoholic beverages" in nl:
        add(80, "alcoholic_beverage")
    if "beer" in nl:
        add(70, "beer_word")
    else:
        add(-120, "not_beer")

    if "regular" in nl:
        add(40, "regular")
    if "all" in nl:
        add(15, "all")

    if "light" in nl:
        add(25 if wants_light else -8, "light_adjust")
    if "higher alcohol" in nl:
        add(25 if wants_strong else -8, "higher_alcohol_adjust")

    for bad in ("bread", "batter", "cheese", "soup", "sauce", "snack", "yeast", "malt powder", "dry", "mix", "cereal"):
        if bad in nl and bad not in ql:
            add(-100, f"bad_{bad.replace(' ', '_')}")
    for bad in ("beef", "beet", "babyfood"):
        if bad in nl and bad not in ql:
            add(-80, f"bad_{bad}")

    return max(score, -380.0), reasons


def _generic_grain_candidate_adjustment(
    n: str,
    query_lower: str,
    requested_state: str,
) -> tuple[float, list[str]]:
    """Keep vague grain queries on plain cooked oats/cereal-with-water rows."""
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    rs = (requested_state or "unknown").lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if "oats" in nl or "oat" in nl:
        add(50, "generic_grain_oats")
    if "cooked" in nl:
        add(40, "generic_grain_cooked")
    if "with water" in nl:
        add(30, "generic_grain_with_water")
    if "without salt" in nl:
        add(20, "generic_grain_without_salt")
    if "cereal" in nl and ("cooked" in nl or "with water" in nl or "oat" in nl):
        add(15, "generic_grain_cereal_cooked_oat")

    for bad in ("protein", "seed", "nut", "snack", "bar", "granola", "muesli"):
        if bad in nl and bad not in query_lower:
            add(-120, f"generic_bad_{bad}")
    if "mix" in nl and "cooked with water" not in nl and "with water" not in nl and "mix" not in query_lower:
        add(-100, "generic_bad_mix")
    for bad in ("meal replacement", "babyfood", "breakfast bar"):
        if bad in nl and bad not in query_lower:
            add(-100, f"generic_bad_{bad.replace(' ', '_')}")
    if rs == "cooked":
        for bad in ("dry", "uncooked", "unprepared"):
            if bad in nl and bad not in query_lower:
                add(-90, f"generic_bad_{bad}")
    if "flour" in nl and "flour" not in query_lower:
        add(-80, "generic_bad_flour")
    if "bran" in nl and "bran" not in query_lower:
        add(-80, "generic_bad_bran")
    if "cereal, ready-to-eat" in nl:
        add(-80, "generic_bad_ready_to_eat")
    if "sugars" in nl:
        add(-80, "generic_bad_sugars")
    if "with milk" in nl and "milk" not in query_lower and "молок" not in query_lower:
        add(-80, "generic_bad_with_milk")

    return max(score, -420.0), reasons


def _fish_candidate_adjustment(
    n: str,
    query_lower: str,
    requested_state: str,
    *,
    candidate_calories_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    smoked_fish_q: bool = False,
) -> tuple[float, list[str]]:
    """Prefer edible fish rows; penalize fish oil, roe, sauces, and fat-only profiles."""
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    rs = (requested_state or "unknown").strip().lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    query_has_oil = any(x in query_lower for x in ("fish oil", "oil", "жир", "масло"))
    fish_species = (
        "salmon",
        "mackerel",
        "herring",
        "trout",
        "whitefish",
        "cod",
        "sardine",
        "haddock",
        "sablefish",
        "cisco",
        "losos",
        "лосос",
        "сельд",
        "скумбр",
        "форел",
    )

    if "fish" in nl:
        add(70, "fish_word")
    for sp in fish_species:
        if sp in nl and sp in query_lower:
            add(50, f"fish_species_{sp.replace(' ', '_')}")
            break
    if any(x in nl for x in ("smoked", "kippered", "lox")) and any(
        x in query_lower for x in ("smoked", "kippered", "копчен", "копчё", "lox")
    ):
        add(45, "fish_smoked_word")
    if rs in ("cooked", "unknown", "smoked") and any(
        x in nl for x in ("cooked", "smoked", "baked", "grilled", "dry heat", "kippered", "lox")
    ):
        add(30, "fish_prepared_state")
    if smoked_fish_q and not any(sp in query_lower for sp in fish_species):
        if any(x in nl for x in ("mackerel", "herring", "whitefish", "sablefish", "cisco", "haddock")):
            add(20, "fish_smoked_fatty_default")

    for bad, tag in (
        ("fish oil", "fish_oil"),
        ("cod liver oil", "cod_liver_oil"),
        ("oil,", "fish_oil_comma"),
    ):
        if bad in nl and not query_has_oil:
            add(-200, tag)
    if "oil" in nl and "fish" in nl and not query_has_oil:
        add(-200, "fish_oil_generic")
    if re.search(r"\bfat\b", nl) and "fat only" not in query_lower and not query_has_oil:
        add(-180, "fish_fat_keyword")
    if "roe" in nl and "roe" not in query_lower and "икра" not in query_lower:
        add(-150, "fish_roe")
    for bad in ("sauce", "soup", "spread", "babyfood", "stew"):
        if bad in nl and bad not in query_lower:
            add(-120, f"fish_bad_{bad}")
    if "salad" in nl and "salad" not in query_lower and "салат" not in query_lower:
        add(-100, "fish_salad")
    if "dried" in nl and "dried" not in query_lower and "сушен" not in query_lower:
        add(-100, "fish_dried")
    if re.search(r"\braw\b", nl) and smoked_fish_q:
        add(-100, "fish_raw_vs_smoked")

    if not query_has_oil:
        if candidate_fat_per100 >= 80 and candidate_protein_per100 <= 5:
            add(-250, "fish_oil_macro_profile")
        if candidate_calories_per100 >= 700:
            add(-250, "fish_too_high_calories")
        if candidate_protein_per100 == 0 and candidate_fat_per100 > 50:
            add(-250, "fish_fat_only_macro")

    if smoked_fish_q:
        if "smoked" in nl or "kippered" in nl or "lox" in nl:
            add(80, "smoked_fish_smoked_row")
        if "fish" in nl:
            add(40, "smoked_fish_fish_row")
        for sp in ("mackerel", "herring", "whitefish", "salmon", "trout", "sablefish", "cisco", "haddock"):
            if sp in nl:
                add(30, f"smoked_fish_{sp}")
                break
        if "canned" in nl and "canned" not in query_lower and "консерв" not in query_lower:
            add(-150, "smoked_fish_canned")
        for bad in ("soup", "sauce", "spread", "babyfood"):
            if bad in nl and bad not in query_lower:
                add(-120, f"smoked_fish_bad_{bad}")

    return max(score, -520.0), reasons


def _soft_drink_candidate_adjustment(
    candidate_name: str,
    query_lower: str,
    *,
    candidate_calories_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_carbs_per100: float = 0.0,
    zero_soft_drink_q: bool = False,
) -> tuple[float, list[str]]:
    """Prefer carbonated cola beverages; penalize oil/fat/syrup/dessert rows."""
    reasons: list[str] = []
    score = 0.0
    nl = candidate_name.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if "beverage" in nl or "beverages" in nl:
        add(80, "soft_drink_beverage")
    if "carbonated" in nl:
        add(70, "soft_drink_carbonated")
    if re.search(r"\bcola\b", nl):
        add(60, "soft_drink_cola")
    if "soft drink" in nl:
        add(40, "soft_drink_phrase")

    for bad, pen in (
        ("oil", 250),
        ("fat", 250),
        ("butter", 220),
    ):
        if bad in nl and bad not in ql:
            add(-pen, f"soft_drink_bad_{bad}")
    if "syrup" in nl and "syrup" not in ql and "сироп" not in ql:
        add(-200, "soft_drink_syrup")
    if "dessert" in nl:
        add(-180, "soft_drink_dessert")
    if "sauce" in nl and "sauce" not in ql:
        add(-180, "soft_drink_sauce")
    for bad in ("powder", "dry mix"):
        if bad in nl:
            add(-150, f"soft_drink_bad_{bad.replace(' ', '_')}")
    if "cocoa" in nl and "cocoa" not in ql:
        add(-150, "soft_drink_cocoa")
    if "coconut" in nl and "coconut" not in ql and not zero_soft_drink_q:
        add(-150, "soft_drink_coconut")

    sugary_expected = not zero_soft_drink_q and not any(
        x in ql for x in ("zero", "diet", "light", "lite", "sugar free", "no sugar", "без сахара", "зеро", "лайт")
    )
    if not zero_soft_drink_q and any(
        x in nl for x in ("low calorie", "diet", "sugar free", "sugar-free", "no sugar")
    ):
        add(-180, "soft_drink_low_calorie_unrequested")
    if sugary_expected and "regular" in nl:
        add(40, "soft_drink_regular_cola")
    if candidate_fat_per100 > 1:
        add(-300, "soft_drink_high_fat")
    if candidate_protein_per100 > 2:
        add(-200, "soft_drink_high_protein")
    if candidate_calories_per100 > 80 and not sugary_expected:
        add(-200, "soft_drink_high_calories")

    _ = candidate_carbs_per100
    return max(score, -900.0), reasons


def _zero_soft_drink_candidate_adjustment(
    candidate_name: str,
    query_lower: str,
    candidate_calories_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_carbs_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Diet/zero cola: low calorie rows only; block fat/oil and regular sweetened cola."""
    reasons: list[str] = []
    score = 0.0
    nl = candidate_name.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if "low calorie" in nl:
        add(120, "zero_low_calorie")
    if "diet" in nl:
        add(100, "zero_diet")
    if "sugar free" in nl or "sugar-free" in nl:
        add(90, "zero_sugar_free")
    if "no sugar" in nl:
        add(80, "zero_no_sugar")
    if re.search(r"\bcola\b", nl):
        add(70, "zero_cola")
    if "carbonated" in nl:
        add(60, "zero_carbonated")

    for bad in ("oil", "fat", "butter"):
        if bad in nl:
            add(-300, f"zero_bad_{bad}")
    if "regular" in nl and "low calorie" not in nl and "diet" not in nl:
        add(-250, "zero_regular_cola")
    if "sweetened" in nl and not any(x in nl for x in ("low calorie", "diet", "sugar free", "sugar-free")):
        add(-220, "zero_sweetened")
    if candidate_carbs_per100 > 2:
        add(-220, "zero_high_carbs")
    if candidate_calories_per100 > 10:
        add(-220, "zero_high_calories")
    for bad in ("syrup", "dessert", "sauce", "powder", "dry mix"):
        if bad in nl:
            add(-180, f"zero_bad_{bad.replace(' ', '_')}")

    if candidate_calories_per100 > 5:
        add(-250, "zero_macro_calories")
    if candidate_carbs_per100 > 1:
        add(-250, "zero_macro_carbs")
    if candidate_fat_per100 > 0.5:
        add(-300, "zero_macro_fat")
    if candidate_protein_per100 > 1:
        add(-200, "zero_macro_protein")

    _ = ql
    return max(score, -950.0), reasons


def _coconut_water_candidate_adjustment(
    candidate_name: str,
    query_lower: str,
    candidate_calories_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_carbs_per100: float = 0.0,
    candidate_fiber_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Prefer coconut water beverage rows; penalize meat/milk/cream/oil/dried coconut."""
    reasons: list[str] = []
    score = 0.0
    nl = candidate_name.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if "coconut water" in nl:
        add(140, "coconut_water_phrase")
    if "liquid from coconuts" in nl:
        add(120, "coconut_water_liquid_from_coconuts")
    if "coconut" in nl and "water" in nl:
        add(100, "coconut_water_words")
    if "beverage" in nl or "beverages" in nl:
        add(80, "coconut_water_beverage")
    if "juice" in nl and "coconut" in nl:
        add(60, "coconut_water_juice")

    for bad, pen in (
        ("coconut oil", 300),
        ("oil,", 280),
    ):
        if bad in nl and "oil" not in ql:
            add(-pen, f"coconut_water_bad_{bad.replace(' ', '_')}")
    if re.search(r"\boil\b", nl) and "oil" not in ql and "масл" not in ql:
        add(-300, "coconut_water_oil")
    for bad, pen in (
        ("coconut meat", 260),
        ("raw coconut", 240),
        ("dried coconut", 240),
        ("desiccated", 240),
    ):
        if bad in nl:
            add(-pen, f"coconut_water_bad_{bad.replace(' ', '_')}")
    if "coconut cream" in nl:
        add(-220, "coconut_water_cream")
    if "coconut milk" in nl and "milk" not in ql and "молок" not in ql:
        add(-200, "coconut_water_milk")
    for bad in ("flour", "butter", "candy", "dessert", "sweetened", "cream"):
        if bad in nl and bad not in ql:
            add(-180 if bad != "cream" else -160, f"coconut_water_bad_{bad}")

    if candidate_fat_per100 > 2:
        add(-300, "coconut_water_high_fat")
    if candidate_fiber_per100 > 2:
        add(-250, "coconut_water_high_fiber")
    if candidate_calories_per100 > 80:
        add(-250, "coconut_water_high_calories")
    if candidate_calories_per100 > 150:
        add(-400, "coconut_water_impossible_calories")
    if candidate_fat_per100 > 10:
        add(-400, "coconut_water_impossible_fat")

    _ = candidate_protein_per100, candidate_carbs_per100, ql
    return max(score, -1000.0), reasons


def _soup_candidate_adjustment(
    candidate_name: str,
    query_lower: str,
    requested_state: str,
    candidate_calories_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_carbs_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Prefer prepared/ready-to-serve soup rows; penalize dry mix, fat, sauce, gravy."""
    reasons: list[str] = []
    score = 0.0
    nl = candidate_name.lower()
    ql = query_lower.lower()
    rs = (requested_state or "unknown").lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if "soup" in nl:
        add(90, "soup_word")
    if "ready-to-serve" in nl or "ready to serve" in nl:
        add(50, "soup_ready_to_serve")
    if "prepared" in nl:
        add(45, "soup_prepared")
    if "cooked" in nl:
        add(40, "soup_cooked")
    if "with water" in nl:
        add(35, "soup_with_water")
    if "prepared with water" in nl:
        add(35, "soup_prepared_with_water")
    if "vegetable" in nl:
        add(30, "soup_vegetable")
    if "broth" in nl and "broth" in ql:
        add(25, "soup_broth")
    for token in ("cabbage", "tomato", "bean", "lentil", "chicken", "beef"):
        if token in nl and token in ql:
            add(20, f"soup_query_{token}")

    if rs in ("cooked", "boiled", "unknown"):
        if any(x in nl for x in ("prepared with equal volume water", "prepared with water", "ready-to-serve", "ready to serve")):
            add(25, "soup_state_prepared")

    for bad, pen in (
        ("dry mix", 220),
        ("dehydrated", 220),
        ("powder", 200),
    ):
        if bad in nl:
            add(-pen, f"soup_bad_{bad.replace(' ', '_')}")
    if "condensed" in nl and "prepared" not in nl:
        add(-180, "soup_condensed_unprepared")
    for bad, pen in (
        ("sauce", 180),
        ("gravy", 180),
        ("oil", 180),
        ("shortening", 180),
    ):
        if bad in nl and bad not in ql:
            add(-pen, f"soup_bad_{bad}")
    if re.search(r"\bfat\b", nl) and "fat" not in ql and "жир" not in ql:
        add(-180, "soup_bad_fat")
    if "cream" in nl and not any(x in ql for x in ("cream", "сливки", "сметана")):
        add(-140, "soup_cream_unrequested")
    if "babyfood" in nl and "baby" not in ql:
        add(-130, "soup_babyfood")
    if "stew" in nl and "stew" not in ql and "рагу" not in ql:
        add(-120, "soup_stew")
    if "canned" in nl and "canned" not in ql and "консерв" not in ql:
        add(-100, "soup_canned_unrequested")
    if "mix" in nl and not any(x in nl for x in ("ready-to-serve", "ready to serve", "prepared")):
        add(-100, "soup_mix")

    query_has_cream = any(x in ql for x in ("cream", "сливки", "сметана", "oil", "масло"))
    if not query_has_cream:
        if candidate_calories_per100 > 220:
            add(-180, "soup_high_calories")
        if candidate_fat_per100 > 15:
            add(-180, "soup_high_fat")
        if candidate_calories_per100 > 400:
            add(-350, "soup_impossible_calories")
        if candidate_fat_per100 > 30:
            add(-350, "soup_impossible_fat")
        if candidate_fat_per100 > 50:
            add(-500, "soup_fat_only_profile")

    _ = candidate_protein_per100, candidate_carbs_per100
    return max(score, -900.0), reasons


def _borscht_candidate_adjustment(
    candidate_name: str,
    query_lower: str,
    candidate_calories_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Borscht-like queries: beet/vegetable soup rows, not beef fat or dry mix."""
    reasons: list[str] = []
    score = 0.0
    nl = candidate_name.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if "borscht" in nl:
        add(120, "borscht_word")
    if "borsch" in nl:
        add(110, "borsch_word")
    if "beet" in nl:
        add(80, "borscht_beet")
    if "soup" in nl:
        add(60, "borscht_soup")
    if "cabbage" in nl:
        add(35, "borscht_cabbage")
    if "vegetable" in nl:
        add(30, "borscht_vegetable")
    if "beef" in nl and any(x in ql for x in ("meat", "beef", "мясом", "говядина", "говяж")):
        add(20, "borscht_beef_in_query")

    for bad, pen in (
        ("dry mix", 250),
        ("dehydrated", 250),
        ("powder", 250),
    ):
        if bad in nl:
            add(-pen, f"borscht_bad_{bad.replace(' ', '_')}")
    for bad, pen in (
        ("sauce", 220),
        ("gravy", 220),
        ("oil", 220),
        ("shortening", 220),
    ):
        if bad in nl and bad not in ql:
            add(-pen, f"borscht_bad_{bad}")
    if re.search(r"\bfat\b", nl) and "fat" not in ql:
        add(-220, "borscht_bad_fat")
    if "condensed" in nl and "prepared" not in nl:
        add(-180, "borscht_condensed_unprepared")
    if "cream" in nl and not any(x in ql for x in ("sour cream", "cream", "сметана", "сливки")):
        add(-140, "borscht_cream_unrequested")
    if "stew" in nl and "stew" not in ql and "рагу" not in ql:
        add(-120, "borscht_stew")
    if "babyfood" in nl:
        add(-120, "borscht_babyfood")
    if "meat only" in nl and "meat" not in ql:
        add(-120, "borscht_meat_only")
    for bad in ("sausage", "beef fat", "pork fat", "tallow", "lard", "separable fat"):
        if bad in nl:
            add(-120, f"borscht_bad_{bad.replace(' ', '_')}")

    if candidate_calories_per100 > 180:
        add(-220, "borscht_high_calories")
    if candidate_fat_per100 > 12:
        add(-220, "borscht_high_fat")
    if candidate_calories_per100 > 300:
        add(-400, "borscht_impossible_calories")
    if candidate_fat_per100 > 25:
        add(-400, "borscht_impossible_fat")

    return max(score, -950.0), reasons


def _beef_candidate_adjustment(
    n: str,
    query_lower: str,
    candidate_carbs_per100: float = 0.0,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if "beef" in nl:
        add(80, "beef_word")
    if "meat only" in nl:
        add(50, "meat_only")
    if "cooked" in nl:
        add(40, "cooked")
    if "stewed" in nl or "roasted" in nl or "braised" in nl:
        add(30, "stewed_or_roasted")

    for bad in ("dish", "mixture", "with sauce", "soup"):
        if bad in nl and bad not in query_lower:
            add(-120, f"beef_bad_{bad.replace(' ', '_')}")
    if "stew" in nl and "vegetable" in nl:
        add(-120, "beef_stew_with_vegetables")

    for bad in ("processed", "canned", "babyfood", "fast food", "burger", "mixed"):
        if bad in nl and bad not in query_lower:
            add(-100, f"beef_bad_{bad.replace(' ', '_')}")
    if "ground" in nl and "ground" not in query_lower:
        add(-100, "beef_ground_mismatch")
    if "carbs" in nl:
        add(-100, "beef_bad_carbs_keyword")
    if (candidate_carbs_per100 or 0) > 0:
        add(-100, "beef_positive_carbs")

    return max(score, -420.0), reasons


def _beef_patty_candidate_adjustment(n: str, query_lower: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    query_is_patty_only = any(x in query_lower for x in ("patty", "котлета"))

    if "patty" in nl:
        add(80, "beef_patty_word")
    if "ground beef" in nl or "beef, ground" in nl:
        add(70, "beef_patty_ground_beef")
    if "cooked" in nl:
        add(50, "beef_patty_cooked")
    if "broiled" in nl or "grilled" in nl:
        add(40, "beef_patty_broiled_grilled")
    if "80%" in nl or "85%" in nl or "lean meat" in nl:
        add(30, "beef_patty_lean_ratio")
    if "hamburger" in nl:
        add(25, "beef_patty_hamburger_word")

    for bad in ("fat", "tallow", "suet", "separable fat", "fat only"):
        if bad in nl and bad not in query_lower:
            add(-150, f"beef_patty_bad_{bad.replace(' ', '_')}")
    if "with bun" in nl and "with bun" not in query_lower:
        add(-120, "beef_patty_with_bun")
    if "cheeseburger" in nl and query_is_patty_only:
        add(-120, "beef_patty_cheeseburger")
    if "sandwich" in nl and "sandwich" not in query_lower:
        add(-120, "beef_patty_sandwich")
    for bad in ("babyfood", "sausage", "meat loaf", "canned"):
        if bad in nl and bad not in query_lower:
            add(-100, f"beef_patty_bad_{bad.replace(' ', '_')}")
    if "breaded" in nl and "breaded" not in query_lower:
        add(-80, "beef_patty_breaded")
    if "fast food" in nl and query_is_patty_only:
        add(-80, "beef_patty_fast_food")

    return max(score, -500.0), reasons


def _porridge_like_grain_adjustment(
    n: str,
    query_lower: str,
    requested_state: str,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    rs = (requested_state or "unknown").lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if rs != "cooked":
        return 0.0, reasons

    if "cooked" in nl:
        add(60, "porridge_cooked")
    if "prepared with water" in nl:
        add(50, "porridge_prepared_with_water")
    if "with water" in nl:
        add(50, "porridge_with_water")
    if "grits" in nl:
        add(40, "porridge_grits")
    if "polenta" in nl:
        add(40, "porridge_polenta")
    if "cornmeal" in nl and "cooked" in nl:
        add(40, "porridge_cornmeal_cooked")
    if "cereal" in nl and "cooked" in nl:
        add(30, "porridge_cereal_cooked")

    for bad in ("dry", "flour", "starch", "dry mix", "ready-to-eat"):
        if bad in nl and bad not in query_lower:
            add(-120, f"porridge_bad_{bad.replace(' ', '_')}")
    for bad in ("bread", "muffin", "pancake", "snack"):
        if bad in nl and bad not in query_lower:
            add(-100, f"porridge_bad_{bad}")
    for bad in ("unprepared", "uncooked"):
        if bad in nl and bad not in query_lower:
            add(-90, f"porridge_bad_{bad}")

    return max(score, -420.0), reasons


def _egg_whole_boiled_adjustment(n: str, ing: str) -> tuple[float, list[str]]:
    """Prefer whole hard-boiled eggs when user asks for boiled eggs."""
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    qi = ing.lower()

    if "hard-boiled" in nl or "hard boiled" in nl:
        score += 45
        reasons.append("+45:egg_hard_boiled")
    elif "boiled" in nl and "whole" in nl:
        score += 40
        reasons.append("+40:egg_boiled_whole")
    elif "whole" in nl and "egg" in nl and ("cooked" in nl or "boiled" in nl):
        score += 30
        reasons.append("+30:egg_whole_cooked")

    wants_white = "white" in qi or "белок" in qi
    wants_yolk = "yolk" in qi or "желток" in qi
    if ("white only" in nl or re.search(r"egg,?\s+white\b", nl)) and not wants_white:
        score -= 70
        reasons.append("-70:egg_white_only_mismatch")
    if ("yolk only" in nl or re.search(r"egg,?\s+yolk\b", nl)) and not wants_yolk:
        score -= 70
        reasons.append("-70:egg_yolk_only_mismatch")
    if "dried" in nl and "egg" in nl and "dried" not in qi:
        score -= 75
        reasons.append("-75:egg_dried")
    if "substitute" in nl and "substitute" not in qi:
        score -= 80
        reasons.append("-80:egg_substitute")
    if "babyfood" in nl and "baby" not in qi:
        score -= 70
        reasons.append("-70:egg_babyfood")
    if "powder" in nl and "powder" not in qi:
        score -= 80
        reasons.append("-80:egg_powder")

    return score, reasons


def _egg_candidate_adjustment(
    n: str,
    query_lower: str,
    requested_state: str,
    *,
    egg_like_q: bool = False,
    plain_whole_egg_q: bool = False,
    candidate_calories_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_carbs_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """
    Aggressive re-ranking for plain egg queries: boost real egg rows,
    penalize potato salad, fast-food, dried/powder, white-only, yolk-only, etc.
    """
    if not egg_like_q:
        return 0.0, []
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    ql = query_lower.lower()
    rs = (requested_state or "unknown").lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    wants_white = "white" in ql or "белок" in ql
    wants_yolk = "yolk" in ql or "желток" in ql

    # Bonuses for matching egg rows
    if "egg" in nl:
        add(120, "egg_word")
    if ("hard-boiled" in nl or "hard boiled" in nl) and rs in ("boiled", "cooked", "unknown"):
        add(100, "egg_hard_boiled_state")
    if "boiled" in nl and rs in ("boiled", "cooked", "unknown"):
        add(90, "egg_boiled_state")
    if "cooked" in nl and rs in ("boiled", "cooked", "unknown"):
        add(80, "egg_cooked_state")
    if "whole" in nl and not wants_white and not wants_yolk:
        add(70, "egg_whole")
    if "fried" in nl and rs == "fried":
        add(50, "egg_fried_state")
    if re.search(r"\braw\b", nl) and rs == "raw":
        add(40, "egg_raw_state")

    if not plain_whole_egg_q:
        # For non-plain egg queries (e.g. egg salad), skip heavy penalties below
        return max(score, -600.0), reasons

    # Penalties for compound / mismatched items (only for plain whole egg queries)
    if "potato salad" in nl:
        add(-250, "egg_potato_salad")
    elif "salad" in nl and "salad" not in ql and "салат" not in ql:
        add(-220, "egg_salad_mismatch")
    if "sandwich" in nl and "sandwich" not in ql:
        add(-220, "egg_sandwich")
    if "burrito" in nl and "burrito" not in ql:
        add(-200, "egg_burrito")
    if "fast food" in nl and "fast food" not in ql:
        add(-200, "egg_fast_food")
    if "babyfood" in nl and "baby" not in ql and "babyfood" not in ql:
        add(-180, "egg_babyfood")
    if "mayonnaise" in nl and "mayonnaise" not in ql:
        add(-180, "egg_mayonnaise")
    if "sauce" in nl and "sauce" not in ql:
        add(-160, "egg_sauce")
    if "substitute" in nl and "substitute" not in ql:
        add(-150, "egg_substitute")
    if "dried" in nl and "dried" not in ql:
        add(-150, "egg_dried")
    if "powder" in nl and "powder" not in ql:
        add(-150, "egg_powder")

    if ("white" in nl or re.search(r"egg,?\s+white", nl)) and not wants_white:
        add(-120, "egg_white_mismatch")
    if ("yolk" in nl or re.search(r"egg,?\s+yolk", nl)) and not wants_yolk:
        add(-120, "egg_yolk_mismatch")

    # Macro sanity checks for plain whole egg
    if candidate_carbs_per100 > 5:
        add(-120, "egg_too_many_carbs")
    if candidate_calories_per100 > 250:
        add(-160, "egg_too_high_calories")
    if candidate_fat_per100 > 20:
        add(-120, "egg_too_high_fat")

    return max(score, -600.0), reasons


def _water_candidate_adjustment(
    candidate_name: str,
    query_lower: str,
    *,
    water_like_q: bool = False,
    candidate_calories_per100: float = 0.0,
    candidate_carbs_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Prefer zero-calorie water rows; penalize watermelon, flavored/sweetened beverages."""
    reasons: list[str] = []
    score = 0.0
    nl = candidate_name.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if not water_like_q:
        return 0.0, reasons

    # Bonuses for plain water rows
    if re.search(r"^water,?\s", nl) or nl.strip() == "water":
        add(150, "water_exact_match")
    if "water, bottled" in nl or "bottled, water" in nl:
        add(100, "water_bottled")
    if "water, tap" in nl or "tap, water" in nl or "tap water" in nl:
        add(100, "water_tap")
    if "drinking water" in nl or "drinking, tap" in nl:
        add(80, "water_drinking")
    if "beverage" in nl and "water" in nl:
        add(60, "water_beverage_water")
    if "naya" in nl or "perrier" in nl or "poland spring" in nl or "evian" in nl:
        add(90, "water_brand_bottled")

    # Penalties for non-water items
    if "watermelon" in nl:
        add(-300, "water_watermelon")
    if "coconut water" in nl and "coconut" not in ql:
        add(-250, "water_coconut_water")
    for bad in ("flavored", "sweetened", "soda", "juice", "soup", "oil", "fat"):
        if bad in nl and bad not in ql:
            add(-220, f"water_bad_{bad}")
    if "beverage" in nl and candidate_calories_per100 > 5:
        add(-180, "water_beverage_high_calories")
    if "tonic" in nl:
        add(-200, "water_tonic")
    if "sparkling" in nl and "sparkling" not in ql:
        add(-100, "water_sparkling")

    # Macro sanity: plain water has ~0 everything
    if candidate_calories_per100 > 1:
        add(-300, "water_high_calories")
    if candidate_carbs_per100 > 0.5:
        add(-300, "water_high_carbs")
    if candidate_fat_per100 > 0:
        add(-300, "water_high_fat")
    if candidate_protein_per100 > 0:
        add(-200, "water_high_protein")

    return max(score, -1000.0), reasons


def _yogurt_candidate_adjustment(
    candidate_name: str,
    query_lower: str,
    *,
    yogurt_like_q: bool = False,
    plain_yogurt_like_q: bool = False,
    soy_yogurt_like_q: bool = False,
    candidate_calories_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_sugar_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Prefer plain/Greek yogurt for plain queries; penalize flavored/soy/SILK for plain queries."""
    reasons: list[str] = []
    score = 0.0
    nl = candidate_name.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if not yogurt_like_q:
        return 0.0, reasons

    # Bonuses for yogurt rows
    if "yogurt" in nl:
        add(100, "yogurt_word")
    if "plain" in nl and plain_yogurt_like_q:
        add(70, "yogurt_plain_word")
    if any(x in nl for x in ("whole milk", "low fat", "lowfat", "nonfat")):
        add(50, "yogurt_milk_type")
    if "greek" in nl:
        add(40, "yogurt_greek")
    if "soy" in nl and soy_yogurt_like_q:
        add(50, "yogurt_soy_aligned")

    # Penalties for plain yogurt query
    if plain_yogurt_like_q:
        if any(x in nl for x in ("soy", "silk")):
            add(-150, "yogurt_plain_soy_silk_penalty")
        if any(x in nl for x in ("peach", "strawberry", "vanilla", "flavored", "raspberry", "blueberry", "cherry", "lime", "banana", "key lime")):
            add(-130, "yogurt_plain_flavored_penalty")
        if "fruit" in nl:
            add(-120, "yogurt_plain_fruit_penalty")
        if any(x in nl for x in ("sweetened", "dessert", "frozen")):
            add(-100, "yogurt_plain_sweet_frozen")
        if "babyfood" in nl:
            add(-120, "yogurt_plain_babyfood")
        # Macro sanity for plain yogurt
        if candidate_calories_per100 > 150:
            add(-120, "yogurt_high_calories")
        if candidate_fat_per100 > 12:
            add(-120, "yogurt_high_fat")
        if candidate_sugar_per100 > 15:
            add(-100, "yogurt_high_sugar")

    return max(score, -500.0), reasons


def _sesame_seed_candidate_adjustment(
    candidate_name: str,
    query_lower: str,
    *,
    sesame_seed_like_q: bool = False,
) -> tuple[float, list[str]]:
    """Prefer sesame seed rows; aggressively penalize cheese/beans/oil/paste for sesame queries."""
    reasons: list[str] = []
    score = 0.0
    nl = candidate_name.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if not sesame_seed_like_q:
        return 0.0, reasons

    # Bonuses
    if "sesame" in nl:
        add(150, "sesame_word")
    if "sesame seeds" in nl or "sesame seed" in nl:
        add(120, "sesame_seeds_phrase")
    if "seeds" in nl or "seed" in nl:
        add(80, "sesame_seed_word")
    if "dried" in nl or re.search(r"\bdry\b", nl):
        add(50, "sesame_dried")
    if "whole" in nl:
        add(30, "sesame_whole")

    # Penalties for non-sesame or non-seed items
    if any(x in nl for x in ("cheese", "queso")):
        add(-300, "sesame_bad_cheese")
    if any(x in nl for x in ("mothbeans", "moth beans")):
        add(-250, "sesame_bad_mothbeans")
    if "mature seeds" in nl and "sesame" not in nl:
        add(-250, "sesame_bad_mature_seeds")
    if re.search(r"\bbean", nl) and "sesame" not in nl:
        add(-220, "sesame_bad_bean")
    if "flour" in nl and "flour" not in ql:
        add(-200, "sesame_bad_flour")
    if any(x in nl for x in ("paste", "tahini", "sesame butter")) and "tahini" not in ql and "paste" not in ql:
        add(-180, "sesame_bad_paste")
    if "oil" in nl and "oil" not in ql:
        add(-180, "sesame_bad_oil")
    if "sauce" in nl and "sauce" not in ql:
        add(-150, "sesame_bad_sauce")
    if "babyfood" in nl:
        add(-150, "sesame_bad_babyfood")
    if "cracker" in nl and "cracker" not in ql:
        add(-120, "sesame_bad_cracker")
    if "chicken" in nl and "chicken" not in ql:
        add(-100, "sesame_bad_chicken")
    if "candy" in nl or "candies" in nl:
        add(-120, "sesame_bad_candy")
    if "meal" in nl and "sesame" not in nl and "meal" not in ql:
        add(-180, "sesame_bad_meal")

    return max(score, -600.0), reasons


def _avocado_candidate_adjustment(
    n: str,
    query_lower: str,
    *,
    avocado_like_q: bool = False,
    oil_like_q: bool = False,
    candidate_calories_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Prefer raw avocado rows for avocado queries; aggressively penalize oil/fat-only profiles."""
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if avocado_like_q:
        # Bonuses for raw avocado rows
        if "avocados" in nl:
            add(120, "avocado_avocados_plural")
        if "avocado" in nl and "raw" in nl:
            add(100, "avocado_avocado_raw")
        if re.search(r"\braw\b", nl):
            add(80, "avocado_raw")
        if "all commercial varieties" in nl:
            add(50, "avocado_all_commercial_varieties")
        if "fruit" in nl and "avocado" in nl:
            add(30, "avocado_fruit")

        # Penalties for non-avocado or processed rows
        if "oil" in nl:
            add(-350, "avocado_oil_row")
        if "dressing" in nl:
            add(-250, "avocado_dressing")
        if "sauce" in nl:
            add(-220, "avocado_sauce")
        if "spread" in nl and "spread" not in ql and "намазка" not in ql:
            add(-220, "avocado_spread")
        if "babyfood" in nl:
            add(-200, "avocado_babyfood")
        if "dip" in nl and "dip" not in ql and "guacamole" not in ql and "гуакамоле" not in ql:
            add(-180, "avocado_dip")
        if "guacamole" in nl and "guacamole" not in ql and "гуакамоле" not in ql:
            add(-180, "avocado_guacamole_mismatch")
        if "powder" in nl:
            add(-150, "avocado_powder")
        if "freeze-dried" in nl or "freeze dried" in nl:
            add(-150, "avocado_freeze_dried")

        # Macro sanity checks
        if candidate_fat_per100 > 40:
            add(-300, "avocado_too_high_fat")
        if candidate_calories_per100 > 350:
            add(-300, "avocado_too_high_calories")
        if candidate_fat_per100 > 80:
            add(-500, "avocado_oil_profile")
        if candidate_protein_per100 == 0 and candidate_fat_per100 > 70:
            add(-500, "avocado_fat_only_profile")

    elif not oil_like_q:
        # Not an avocado or oil query: penalize oil rows that slip through
        if "oil" in nl and "avocado" in nl:
            add(-200, "avocado_oil_non_oil_query")

    return max(score, -700.0), reasons


def _grain_cooked_extra(n: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    if _word_cooked(n) or ", cooked" in n:
        score += 45
        reasons.append("+45:grain_cooked")
    if "boiled" in n:
        score += 35
        reasons.append("+35:grain_boiled")
    if "dry" in n or re.search(r"\bdry\b", n):
        score -= 80
        reasons.append("-80:grain_dry")
    if "uncooked" in n:
        score -= 80
        reasons.append("-80:grain_uncooked")
    if "unprepared" in n:
        score -= 80
        reasons.append("-80:grain_unprepared")
    if "flour" in n:
        score -= 60
        reasons.append("-60:grain_flour")
    if "dry mix" in n:
        score -= 60
        reasons.append("-60:grain_dry_mix")
    return score, reasons


def _category_common_adjustment(
    candidate_name: str,
    *,
    query: str,
    ingredient_input: str,
    categories: set[str] | frozenset[str],
    requested_state: str,
) -> tuple[float, list[str]]:
    """
    Safe generic layer on top of state-aware scoring.
    Keeps existing specialized helpers intact, but adds broad category penalties/bonuses.
    """
    reasons: list[str] = []
    score = 0.0
    nl = candidate_name.lower()
    ql = query.lower()
    il = ingredient_input.lower()
    rs = (requested_state or "unknown").lower()
    cats = set(categories)

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    def q_has(*words: str) -> bool:
        blob = f"{ql} {il}"
        return any(w in blob for w in words)

    # Coconut water
    if "coconut_water" in cats:
        if "coconut water" in nl or "liquid from coconuts" in nl:
            add(50, "cat_coconut_water_row")
        if "beverage" in nl:
            add(30, "cat_coconut_water_beverage")
        for bad in (
            "oil",
            "coconut oil",
            "coconut meat",
            "dried",
            "desiccated",
            "coconut milk",
            "coconut cream",
            "flour",
            "butter",
        ):
            if bad in nl and not q_has(bad):
                add(-120, f"cat_coconut_water_bad_{bad.replace(' ', '_')}")

    # Soft drinks / zero-calorie cola
    if "zero_soft_drink" in cats:
        if any(x in nl for x in ("low calorie", "diet", "sugar free", "sugar-free", "no sugar")):
            add(40, "cat_zero_soft_drink_marker")
        if "carbonated" in nl or "beverage" in nl:
            add(30, "cat_zero_soft_drink_beverage")
        for bad in ("oil", "fat", "butter", "syrup", "dessert", "sauce", "powder", "dry mix"):
            if bad in nl and not q_has(bad):
                add(-120, f"cat_zero_bad_{bad.replace(' ', '_')}")
        if "regular" in nl and not any(x in nl for x in ("low calorie", "diet", "sugar free")):
            add(-100, "cat_zero_regular")
    elif "soft_drink" in cats:
        if any(x in nl for x in ("beverage", "carbonated", "cola")):
            add(30, "cat_soft_drink_row")
        for bad in ("oil", "fat", "butter", "syrup", "dessert", "sauce"):
            if bad in nl and not q_has(bad):
                add(-100, f"cat_soft_drink_bad_{bad}")

    # Soup / prepared dishes
    if "soup" in cats or "prepared_soup" in cats or "prepared_dish" in cats:
        if "soup" in nl:
            add(40, "cat_soup_word")
        if any(x in nl for x in ("ready-to-serve", "ready to serve", "prepared with water", "prepared with equal volume water")):
            add(35, "cat_soup_prepared")
        if rs in ("cooked", "boiled", "unknown") and any(
            x in nl for x in ("prepared", "cooked", "with water", "ready-to-serve", "ready to serve")
        ):
            add(25, "cat_soup_state_aligned")
        for bad, pen in (
            ("dry mix", 120),
            ("dehydrated", 120),
            ("powder", 110),
            ("sauce", 100),
            ("gravy", 100),
            ("shortening", 100),
        ):
            if bad in nl and not q_has(bad):
                add(-pen, f"cat_soup_bad_{bad.replace(' ', '_')}")
        if "condensed" in nl and "prepared" not in nl and not q_has("condensed"):
            add(-90, "cat_soup_condensed")
        if re.search(r"\bfat\b", nl) and not q_has("fat", "oil", "масло", "жир"):
            add(-100, "cat_soup_fat")
        if "oil" in nl and not q_has("oil", "масло"):
            add(-100, "cat_soup_oil")

    # Meat / beef
    if "meat" in cats or "beef" in cats:
        if "meat only" in nl:
            add(40, "cat_meat_only")
        if rs in ("cooked", "boiled", "fried", "baked", "grilled", "roasted") and any(
            x in nl for x in ("cooked", "stewed", "roasted", "grilled", "fried", "braised")
        ):
            add(35, "cat_meat_state_aligned")
        if "beef" in cats and "beef" in nl:
            add(30, "cat_beef_word")
        for bad in ("dish", "mixture", "soup", "sauce"):
            if bad in nl and not q_has(bad):
                add(-90, f"cat_meat_bad_{bad}")
        for bad in ("babyfood", "fast food", "processed"):
            if bad in nl and not q_has(bad):
                add(-80, f"cat_meat_bad_{bad.replace(' ', '_')}")
        if "canned" in nl and rs != "canned":
            add(-80, "cat_meat_canned")
        if "burger" in nl and not q_has("burger"):
            add(-80, "cat_meat_burger")
        if "ground" in nl and not q_has("ground", "minced", "farsh", "фарш"):
            add(-70, "cat_meat_ground")
        if any(x in nl for x in ("breaded", "battered")):
            add(-70, "cat_meat_breaded")
        if "beef" in cats and not q_has("rice", "pasta", "potato", "карто", "рис", "макарон"):
            for bad in ("rice", "pasta", "potato"):
                if bad in nl:
                    add(-70, f"cat_meat_with_{bad}")

    # Poultry
    if "poultry" in cats:
        if any(x in nl for x in ("chicken", "turkey")):
            add(25, "cat_poultry_plain")
        for bad in ("nuggets", "breaded", "fast food", "patty", "sausage", "spread"):
            if bad in nl and not q_has(bad):
                add(-80, f"cat_poultry_bad_{bad.replace(' ', '_')}")
        if "canned" in nl and rs != "canned":
            add(-80, "cat_poultry_canned")

    # Seafood / fish
    if any(x in cats for x in ("seafood", "fish", "shrimp", "tuna")):
        if any(x in nl for x in ("fish", "seafood", "shrimp", "tuna", "crustaceans")):
            add(20, "cat_seafood_plain")
        for bad in ("breaded", "battered", "tempura", "sauce", "salad", "soup", "mixture", "fast food"):
            if bad in nl and not q_has(bad):
                add(-70, f"cat_seafood_bad_{bad.replace(' ', '_')}")

    # Grains
    if "grain" in cats:
        if rs == "cooked" and any(x in nl for x in ("cooked", "boiled", "with water")):
            add(20, "cat_grain_cooked")
        if rs == "cooked":
            for bad in ("dry", "uncooked", "unprepared", "flour", "dry mix"):
                if bad in nl and not q_has(bad):
                    add(-60, f"cat_grain_bad_{bad.replace(' ', '_')}")

    # Legumes
    if "legume" in cats and rs in ("cooked", "boiled"):
        if any(x in nl for x in ("cooked", "boiled", "canned")):
            add(20, "cat_legume_prepared")
        for bad in ("raw", "dry", "unprepared"):
            if bad in nl and not q_has(bad):
                add(-60, f"cat_legume_bad_{bad}")

    # Vegetables
    if "vegetable" in cats:
        if rs in ("raw", "cooked", "boiled", "canned"):
            if rs == "raw" and "raw" in nl:
                add(15, "cat_veg_raw")
            if rs in ("cooked", "boiled") and any(x in nl for x in ("cooked", "boiled", "steamed")):
                add(15, "cat_veg_cooked")
            if rs == "canned" and "canned" in nl:
                add(15, "cat_veg_canned")
        for bad in ("snacks", "chips", "flour", "bread", "soup", "sauce", "babyfood"):
            if bad in nl and not q_has(bad):
                add(-60, f"cat_veg_bad_{bad}")

    # Dairy / cheese / cottage cheese
    if "dairy" in cats or "cheese" in cats or "cottage_cheese" in cats:
        if "cottage_cheese" not in cats:
            for bad in ("dessert", "cheesecake"):
                if bad in nl and not q_has(bad):
                    add(-60, f"cat_dairy_bad_{bad}")
            if "processed" in nl and not q_has("processed"):
                add(-50, "cat_dairy_processed")

    # Seed / nut
    if "seed" in cats or "nut" in cats:
        if any(x in nl for x in ("seed", "seeds", "kernel", "kernels", "nut", "nuts")):
            add(20, "cat_seed_nut_plain")
        for bad in ("oil", "flour", "meal", "butter", "beverage", "soup", "babyfood"):
            if bad in nl and not q_has(bad):
                add(-70, f"cat_seed_nut_bad_{bad}")

    # Beverages
    if "beverage" in cats or "tea" in cats or "coffee" in cats:
        if any(x in nl for x in ("brewed", "prepared with tap water", "prepared with distilled water")):
            add(20, "cat_beverage_brewed")
        for bad in ("powder", "dry mix", "milkshake mix", "protein powder", "cereal", "dessert"):
            if bad in nl and not q_has(bad):
                add(-70, f"cat_beverage_bad_{bad.replace(' ', '_')}")

    return score, reasons


def _beef_steak_candidate_adjustment(
    n: str,
    query_lower: str,
    requested_state: str,
    *,
    beef_steak_like_q: bool = False,
    fat_tallow_like_q: bool = False,
    candidate_calories_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_carbs_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Steer beef steak queries to cooked/grilled steak rows; penalize tallow/fat-only rows."""
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    rs = (requested_state or "unknown").lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    if not beef_steak_like_q:
        return 0.0, reasons

    # Bonuses for matching steak rows
    if "steak" in nl:
        add(120, "steak_word")
    if "beef" in nl:
        add(100, "steak_beef_word")
    if "grilled" in nl and rs == "grilled":
        add(70, "steak_grilled_aligned")
    if "broiled" in nl and rs in ("grilled", "cooked", "unknown"):
        add(65, "steak_broiled_aligned")
    if "cooked" in nl:
        add(55, "steak_cooked_word")
    if any(x in nl for x in ("sirloin", "ribeye", "rib eye", "tenderloin", "loin", "round")):
        add(40, "steak_cut_word")
    if any(x in nl for x in ("lean and fat", "lean only")):
        add(35, "steak_lean_fat_desc")
    if "separable lean" in nl:
        add(25, "steak_separable_lean")

    # Penalties for fat/tallow rows
    if "tallow" in nl:
        add(-400, "steak_tallow_penalty")
    if "fat, beef tallow" in nl:
        add(-400, "steak_fat_beef_tallow")
    if any(x in nl for x in ("beef fat", "separable fat", "fat only")):
        add(-350, "steak_beef_fat_penalty")
    if "suet" in nl:
        add(-300, "steak_suet_penalty")
    if "lard" in nl:
        add(-250, "steak_lard_penalty")
    if "oil" in nl and "oil" not in query_lower:
        add(-220, "steak_oil_penalty")
    if "sausage" in nl:
        add(-180, "steak_sausage_penalty")
    if "burger" in nl and "burger" not in query_lower:
        add(-180, "steak_burger_penalty")
    if "patty" in nl and "patty" not in query_lower:
        add(-180, "steak_patty_penalty")
    if "meat loaf" in nl:
        add(-160, "steak_meatloaf_penalty")
    if any(x in nl for x in ("canned", "babyfood", "sauce")):
        if not any(x in query_lower for x in ("canned", "babyfood", "sauce")):
            add(-150, "steak_canned_babyfood_sauce")
    if any(x in nl for x in ("dish", "mixture")):
        if not any(x in query_lower for x in ("dish", "mixture")):
            add(-150, "steak_dish_mixture")

    # Macro sanity checks (skip if user explicitly wants fat/tallow)
    if not fat_tallow_like_q and not any(x in query_lower for x in ("fat", "tallow", "жир", "oil", "масло")):
        if candidate_fat_per100 > 50:
            add(-300, "steak_too_high_fat")
        if candidate_calories_per100 > 500:
            add(-300, "steak_too_high_calories")
        if candidate_protein_per100 < 10 and candidate_fat_per100 > 50:
            add(-500, "steak_fat_only_profile")
        if candidate_carbs_per100 > 5:
            add(-120, "steak_unexpected_carbs")

    return max(score, -900.0), reasons


def _passion_fruit_candidate_adjustment(
    n: str,
    query_lower: str,
    *,
    passion_fruit_like_q: bool = False,
    candidate_calories_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Prefer raw passion fruit rows; aggressively penalize beverages/juices/drinks."""
    if not passion_fruit_like_q:
        return 0.0, []
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    # Bonuses
    if "passion-fruit" in nl:
        add(150, "passion_fruit_hyphen")
    elif "passion fruit" in nl:
        add(140, "passion_fruit_phrase")
    if re.search(r"\braw\b", nl) or ", raw" in nl:
        add(100, "passion_fruit_raw")
    if "fruit" in nl and "passion" in nl:
        add(80, "passion_fruit_word")
    if "granadilla" in nl:
        add(50, "passion_fruit_granadilla")

    # Penalties for beverage/juice rows
    if any(x in nl for x in ("beverage", "beverages")):
        add(-300, "passion_fruit_beverage_penalty")
    if "juice" in nl:
        add(-280, "passion_fruit_juice_penalty")
    if "drink" in nl:
        add(-260, "passion_fruit_drink_penalty")
    if "v8" in nl:
        add(-240, "passion_fruit_v8_penalty")
    if any(x in nl for x in ("splash", "cocktail")):
        add(-220, "passion_fruit_splash_cocktail_penalty")
    if "nectar" in nl:
        add(-200, "passion_fruit_nectar_penalty")
    if "syrup" in nl:
        add(-180, "passion_fruit_syrup_penalty")
    if "sweetened" in nl:
        add(-160, "passion_fruit_sweetened_penalty")

    # Macro sanity: raw passion fruit ~97 kcal/100g, fat ~0.1g
    if candidate_calories_per100 > 150:
        add(-180, "passion_fruit_high_calories")
    if candidate_fat_per100 > 5:
        add(-180, "passion_fruit_high_fat")

    _ = query_lower
    return max(score, -700.0), reasons


def _crepe_candidate_adjustment(
    n: str,
    query_lower: str,
    *,
    crepe_like_q: bool = False,
    pancake_like_q: bool = False,
    candidate_calories_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_sugar_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Prefer cooked crepe/pancake rows; aggressively penalize cookies/crackers/KEEBLER."""
    if not crepe_like_q and not pancake_like_q:
        return 0.0, []
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    # Bonuses
    if "crepe" in nl or "crepes" in nl:
        add(160, "crepe_word")
    elif "pancake" in nl:
        add(120, "pancake_word")
    if "plain" in nl:
        add(80, "crepe_plain")
    if "prepared" in nl or "cooked" in nl:
        add(60, "crepe_prepared_cooked")
    if "from recipe" in nl or "from mix" in nl:
        add(40, "crepe_from_recipe_mix")

    # Penalties for cookie/cracker/snack rows
    if any(x in nl for x in ("cookie", "cookies")):
        add(-320, "crepe_cookie_penalty")
    if "sweet cremes" in nl:
        add(-300, "crepe_sweet_cremes_penalty")
    if "keebler" in nl:
        add(-260, "crepe_keebler_penalty")
    if any(x in nl for x in ("cracker", "wafer")):
        add(-220, "crepe_cracker_wafer_penalty")
    if "cereal" in nl and "cereal" not in ql:
        add(-200, "crepe_cereal_penalty")
    if "cake" in nl and "cake" not in ql:
        add(-180, "crepe_cake_penalty")
    if "dessert" in nl and "dessert" not in ql:
        add(-160, "crepe_dessert_penalty")
    if "frozen" in nl and "frozen" not in ql:
        add(-150, "crepe_frozen_penalty")

    # Macro sanity: cooked crepes/pancakes ~190-270 kcal/100g
    if candidate_calories_per100 > 450:
        add(-160, "crepe_too_high_calories")
    if candidate_fat_per100 > 25:
        add(-140, "crepe_too_high_fat")
    if candidate_sugar_per100 > 30:
        add(-120, "crepe_too_high_sugar")

    return max(score, -700.0), reasons


def _chocolate_truffle_candidate_adjustment(
    n: str,
    query_lower: str,
    *,
    chocolate_truffle_like_q: bool = False,
    chocolate_candy_like_q: bool = False,
    candidate_calories_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Prefer chocolate candy/truffle rows; aggressively penalize syrup/fudge-type/sauce."""
    if not chocolate_truffle_like_q and not chocolate_candy_like_q:
        return 0.0, []
    reasons: list[str] = []
    score = 0.0
    nl = n.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    # Bonuses
    if "chocolate" in nl and "truffle" in nl:
        add(180, "chocolate_truffle_phrase")
    elif "candies" in nl and "chocolate" in nl:
        add(130, "candies_chocolate_phrase")
    elif "candy" in nl and "chocolate" in nl:
        add(120, "candy_chocolate_phrase")
    if "confectionery" in nl:
        add(90, "chocolate_confectionery")
    if "chocolate" in nl:
        add(80, "chocolate_word")
    if any(x in nl for x in ("milk chocolate", "dark chocolate")):
        add(50, "chocolate_type")
    if "prepared-from-recipe" in nl and "truffle" in nl:
        add(60, "chocolate_truffle_recipe")

    # Penalties for non-candy rows
    if "syrup" in nl and "syrup" not in ql:
        add(-320, "chocolate_syrup_penalty")
    if "fudge-type" in nl:
        add(-300, "chocolate_fudge_type_penalty")
    if "sauce" in nl and "sauce" not in ql:
        add(-280, "chocolate_sauce_penalty")
    if "topping" in nl and "topping" not in ql:
        add(-260, "chocolate_topping_penalty")
    if any(x in nl for x in ("powder", "cocoa powder")) and "powder" not in ql:
        add(-220, "chocolate_powder_penalty")
    if "beverage" in nl and "beverage" not in ql:
        add(-200, "chocolate_beverage_penalty")
    if "baking" in nl and "baking" not in ql:
        add(-180, "chocolate_baking_penalty")
    if "unsweetened" in nl and "unsweetened" not in ql:
        add(-180, "chocolate_unsweetened_penalty")
    if any(x in nl for x in ("oil", "butter")) and not any(x in ql for x in ("oil", "butter")):
        add(-160, "chocolate_oil_butter_penalty")

    # Macro sanity: chocolate candy should be high calorie (>400 kcal/100g)
    if candidate_calories_per100 < 250:
        add(-120, "chocolate_too_low_calories")

    return max(score, -800.0), reasons


def _kombucha_candidate_adjustment(
    candidate_name: str,
    query_lower: str,
    *,
    kombucha_like_q: bool = False,
    kombucha_zero_like_q: bool = False,
    candidate_calories_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_carbs_per100: float = 0.0,
    candidate_sugar_per100: float = 0.0,
    candidate_fiber_per100: float = 0.0,
) -> tuple[float, list[str]]:
    """Prefer tea/beverage rows for kombucha queries; aggressively penalize grain/cereal/flour rows."""
    if not kombucha_like_q:
        return 0.0, []
    reasons: list[str] = []
    score = 0.0
    nl = candidate_name.lower()
    ql = query_lower.lower()

    def add(val: float, tag: str) -> None:
        nonlocal score
        score += val
        reasons.append(f"{val:+.0f}:{tag}")

    # Bonuses for beverage/tea rows
    if "kombucha" in nl:
        add(180, "kombucha_word")
    elif "fermented tea" in nl:
        add(140, "kombucha_fermented_tea")
    elif "tea" in nl and "beverage" in nl:
        add(100, "kombucha_tea_beverage")
    elif "beverage" in nl or "beverages" in nl:
        add(90, "kombucha_beverage")
    elif "drink" in nl:
        add(70, "kombucha_drink")
    elif "tea" in nl:
        add(50, "kombucha_tea")

    # Penalties for completely wrong food categories
    if "buckwheat" in nl:
        add(-350, "kombucha_buckwheat_penalty")
    if "groats" in nl:
        add(-320, "kombucha_groats_penalty")
    if "cereal" in nl or "grain" in nl:
        add(-300, "kombucha_cereal_grain_penalty")
    if "flour" in nl:
        add(-280, "kombucha_flour_penalty")
    if re.search(r"\bdry\b", nl) and not any(x in nl for x in ("beverage", "drink", "tea")):
        add(-260, "kombucha_dry_non_beverage_penalty")
    # raw mango/kiwi row without beverage context
    if ("mango" in nl or "kiwi" in nl) and not any(x in nl for x in ("beverage", "drink", "tea", "kombucha")):
        add(-240, "kombucha_raw_fruit_penalty")
    if re.search(r"\braw\b", nl) and not any(x in nl for x in ("beverage", "drink", "tea", "kombucha")):
        add(-240, "kombucha_raw_non_beverage_penalty")
    # juice only if user didn't ask for juice
    if "juice" in nl and "juice" not in ql and "сок" not in ql:
        add(-220, "kombucha_juice_mismatch")
    if "syrup" in nl:
        add(-220, "kombucha_syrup_penalty")
    if "powder" in nl or "dry mix" in nl:
        add(-200, "kombucha_powder_penalty")
    if "smoothie" in nl:
        add(-180, "kombucha_smoothie_penalty")
    if "soda" in nl and "soda" not in ql:
        add(-180, "kombucha_soda_mismatch")

    # Macro sanity checks for kombucha
    if candidate_calories_per100 > 80:
        add(-200, "kombucha_too_high_calories")
    if candidate_fat_per100 > 1:
        add(-300, "kombucha_unexpected_fat")
    if candidate_protein_per100 > 2:
        add(-200, "kombucha_unexpected_protein")
    if candidate_fiber_per100 > 1:
        add(-200, "kombucha_unexpected_fiber")
    if candidate_carbs_per100 > 25:
        add(-180, "kombucha_too_many_carbs")

    # Additional penalties for zero-sugar kombucha
    if kombucha_zero_like_q:
        if candidate_calories_per100 > 10:
            add(-250, "kombucha_zero_high_calories")
        if candidate_carbs_per100 > 3:
            add(-250, "kombucha_zero_high_carbs")
        if candidate_sugar_per100 > 2:
            add(-250, "kombucha_zero_high_sugar")

    return max(score, -900.0), reasons


def state_score(
    requested_state: str,
    candidate_name: str,
    *,
    query: str,
    ingredient_input: str = "",
    candidate_carbs_per100: float = 0.0,
    candidate_calories_per100: float = 0.0,
    candidate_protein_per100: float = 0.0,
    candidate_fat_per100: float = 0.0,
    candidate_fiber_per100: float = 0.0,
    categories: tuple[str, ...] = (),
    is_grain_like: bool,
    is_legume_like: bool = False,
    is_poultry_breast_query: bool = False,
    is_tuna_like: bool = False,
    seafood_like_q: bool = False,
    corn_like_q: bool = False,
    beer_q: bool = False,
    generic_grain_query: bool = False,
    beef_q: bool = False,
    beef_patty_q: bool = False,
    soup_like_q: bool = False,
    borscht_like_q: bool = False,
    soft_drink_like_q: bool = False,
    zero_soft_drink_like_q: bool = False,
    coconut_water_like_q: bool = False,
    coconut_meat_like_q: bool = False,
    coconut_milk_like_q: bool = False,
    coconut_oil_like_q: bool = False,
    fish_like_q: bool = False,
    smoked_fish_q: bool = False,
    porridge_like_grain_q: bool = False,
    tea_drink_q: bool = False,
    cottage_cheese_q: bool = False,
    banana_fruit_q: bool = False,
    seed_kernel_q: bool = False,
    avocado_like_q: bool = False,
    oil_like_q: bool = False,
    water_like_q: bool = False,
    yogurt_like_q: bool = False,
    plain_yogurt_like_q: bool = False,
    soy_yogurt_like_q: bool = False,
    sesame_seed_like_q: bool = False,
    candidate_sugar_per100: float = 0.0,
    egg_like_q: bool = False,
    plain_whole_egg_q: bool = False,
    beef_steak_like_q: bool = False,
    fat_tallow_like_q: bool = False,
    passion_fruit_like_q: bool = False,
    crepe_like_q: bool = False,
    pancake_like_q: bool = False,
    chocolate_truffle_like_q: bool = False,
    chocolate_candy_like_q: bool = False,
    kombucha_like_q: bool = False,
    kombucha_zero_like_q: bool = False,
) -> tuple[float, list[str]]:
    """
    Returns (score_adjustment, reason strings).
    Text similarity is handled elsewhere; this is additive state alignment.
    """
    rs = (requested_state or "unknown").strip().lower()
    n = candidate_name.lower()
    query_lower = query.lower()
    reasons: list[str] = []

    cooked_soft = ("cooked", "boiled", "steamed", "simmered")
    cooked_hard = ("baked", "grilled", "roasted", "fried", "pan-fried", "pan fried")
    canned_markers = ("canned", "drained solids")

    def add(score: float, reason: str) -> None:
        nonlocal reasons
        reasons.append(f"{score:+.0f}:{reason}")

    score = 0.0
    ing = (ingredient_input or query).strip().lower()

    has_dry = _has_any(n, ("dry", "uncooked", "unprepared", "unenriched")) or "flour" in n or "powder" in n
    has_raw = bool(re.search(r"\braw\b", n)) or "fresh" in n
    has_cooked = any(x in n for x in cooked_soft) or any(x in n for x in cooked_hard)
    has_boiled = "boiled" in n
    has_fried = "fried" in n or "pan-fried" in n
    has_baked = "baked" in n
    has_grilled = "grilled" in n
    has_roasted = "roasted" in n
    has_canned = any(x in n for x in canned_markers)

    common, common_reasons = _category_common_adjustment(
        candidate_name,
        query=query,
        ingredient_input=ingredient_input,
        categories=frozenset(categories),
        requested_state=rs,
    )
    score += common
    reasons.extend(common_reasons)

    if rs != "unknown":
        if rs == "cooked":
            if any(x in n for x in cooked_soft):
                score += 30
                add(30, "cooked/boiled/steamed")
            elif any(x in n for x in cooked_hard):
                score += 20
                add(20, "baked/grilled/roasted/fried")
            elif has_dry or has_raw:
                score -= 45
                add(-45, "dry/raw/unprepared")
            elif not has_cooked:
                score += 10
                add(10, "no explicit state")
            if has_dry and not _query_implies_flour_powder(query) and any(
                w in n for w in ("flour", "powder", "mix")
            ):
                score -= 25
                add(-25, "flour/powder vs non-flour query")
            if is_grain_like:
                gs, gr = _grain_cooked_extra(n)
                score += gs
                reasons.extend(gr)

        elif rs == "boiled":
            if has_boiled:
                score += 35
                add(35, "boiled")
            elif "cooked" in n or "steamed" in n:
                score += 25
                add(25, "cooked-like")
            elif has_dry or has_raw:
                score -= 40
                add(-40, "dry/raw/unprepared")
            if has_fried or has_grilled or has_baked or has_roasted:
                score -= 15
                add(-15, "fried/grilled/baked/roasted")

        elif rs == "fried":
            if has_fried:
                score += 35
                add(35, "fried")
            elif "cooked" in n:
                score += 15
                add(15, "cooked")
            elif has_dry or has_raw or "unprepared" in n:
                score -= 35
                add(-35, "raw/dry/unprepared")
            if has_boiled:
                score -= 10
                add(-10, "boiled")

        elif rs == "baked":
            if has_baked:
                score += 35
                add(35, "baked")
            elif "cooked" in n:
                score += 15
                add(15, "cooked")
            elif has_dry or has_raw or "unprepared" in n:
                score -= 35
                add(-35, "raw/dry/unprepared")

        elif rs == "grilled":
            if has_grilled:
                score += 35
                add(35, "grilled")
            elif "cooked" in n:
                score += 15
                add(15, "cooked")
            elif has_dry or has_raw or "unprepared" in n:
                score -= 35
                add(-35, "raw/dry/unprepared")

        elif rs == "roasted":
            if has_roasted:
                score += 35
                add(35, "roasted")
            elif "cooked" in n:
                score += 20
                add(20, "cooked")
            elif has_dry or has_raw or "unprepared" in n:
                score -= 35
                add(-35, "raw/dry/unprepared")

        elif rs == "raw":
            if re.search(r"\braw\b", n) or ", raw" in n:
                score += 35
                add(35, "raw")
            elif "fresh" in n:
                score += 15
                add(15, "fresh")
            if has_cooked or has_boiled or has_fried or has_baked or has_grilled or has_roasted:
                score -= 35
                add(-35, "cooked family")
            if has_canned or has_dry or "unprepared" in n:
                score -= 20
                add(-20, "canned/dry/unprepared")

        elif rs == "dry":
            if has_dry or "uncooked" in n or "unprepared" in n:
                score += 35
                add(35, "dry/uncooked")
            if _query_implies_flour_powder(query) and any(w in n for w in ("flour", "powder", "mix")):
                score += 20
                add(20, "flour/powder aligned")
            if "cooked" in n or has_boiled:
                score -= 35
                add(-35, "cooked/boiled")
            if has_canned:
                score -= 20
                add(-20, "canned")

        elif rs == "canned":
            if has_canned:
                score += 40
                add(40, "canned")
            if "solids and liquids" in n or "drained" in n:
                score += 15
                add(15, "packaged liquid/solids")
            if has_raw or has_dry:
                score -= 30
                add(-30, "raw/dry")

        elif rs == "smoked":
            if "smoked" in n or "kippered" in n or "lox" in n:
                score += 40
                add(40, "smoked_row")
            elif "dry heat" in n or "cooked" in n:
                score += 20
                add(20, "smoked_cooked_fallback")
            if has_raw and "smoked" not in n:
                score -= 35
                add(-35, "smoked_vs_raw")

    if is_beverage_like_query(ing) and not query_implies_beverage_powder_or_dry_mix(ing):
        bb, br = _beverage_candidate_adjustment(n)
        score += bb
        reasons.extend(br)

    if is_egg_like_name(ing) and rs in ("boiled", "cooked"):
        eb, er = _egg_whole_boiled_adjustment(n, ing)
        score += eb
        reasons.extend(er)

    if is_tuna_like and rs == "canned":
        tu, tr = _tuna_canned_adjustment(n, ing, query_lower)
        score += tu
        reasons.extend(tr)

    if seafood_like_q:
        sh, shr = _shrimp_candidate_adjustment(n, query_lower, rs)
        score += sh
        reasons.extend(shr)

    if corn_like_q:
        co, cor = _corn_candidate_adjustment(n, query_lower, rs)
        score += co
        reasons.extend(cor)

    if beer_q:
        be, ber = _beer_candidate_adjustment(n, query_lower)
        score += be
        reasons.extend(ber)

    if generic_grain_query:
        gg, ggr = _generic_grain_candidate_adjustment(n, query_lower, rs)
        score += gg
        reasons.extend(ggr)

    if coconut_water_like_q:
        cw, cwr = _coconut_water_candidate_adjustment(
            n,
            query_lower,
            candidate_calories_per100=candidate_calories_per100,
            candidate_protein_per100=candidate_protein_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_carbs_per100=candidate_carbs_per100,
            candidate_fiber_per100=candidate_fiber_per100,
        )
        score += cw
        reasons.extend(cwr)

    if soft_drink_like_q:
        sd, sdr = _soft_drink_candidate_adjustment(
            n,
            query_lower,
            candidate_calories_per100=candidate_calories_per100,
            candidate_protein_per100=candidate_protein_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_carbs_per100=candidate_carbs_per100,
            zero_soft_drink_q=zero_soft_drink_like_q,
        )
        score += sd
        reasons.extend(sdr)
    if zero_soft_drink_like_q:
        zd, zdr = _zero_soft_drink_candidate_adjustment(
            n,
            query_lower,
            candidate_calories_per100=candidate_calories_per100,
            candidate_protein_per100=candidate_protein_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_carbs_per100=candidate_carbs_per100,
        )
        score += zd
        reasons.extend(zdr)

    if soup_like_q:
        sp, spr = _soup_candidate_adjustment(
            n,
            query_lower,
            rs,
            candidate_calories_per100=candidate_calories_per100,
            candidate_protein_per100=candidate_protein_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_carbs_per100=candidate_carbs_per100,
        )
        score += sp
        reasons.extend(spr)
    if borscht_like_q:
        bo, bor = _borscht_candidate_adjustment(
            n,
            query_lower,
            candidate_calories_per100=candidate_calories_per100,
            candidate_fat_per100=candidate_fat_per100,
        )
        score += bo
        reasons.extend(bor)

    if beef_q:
        bf, bfr = _beef_candidate_adjustment(n, query_lower, candidate_carbs_per100)
        score += bf
        reasons.extend(bfr)
    if beef_patty_q:
        bp, bpr = _beef_patty_candidate_adjustment(n, query_lower)
        score += bp
        reasons.extend(bpr)

    if beef_steak_like_q or fat_tallow_like_q:
        bs, bsr = _beef_steak_candidate_adjustment(
            n,
            query_lower,
            rs,
            beef_steak_like_q=beef_steak_like_q,
            fat_tallow_like_q=fat_tallow_like_q,
            candidate_calories_per100=candidate_calories_per100,
            candidate_protein_per100=candidate_protein_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_carbs_per100=candidate_carbs_per100,
        )
        score += bs
        reasons.extend(bsr)

    if fish_like_q:
        ff, ffr = _fish_candidate_adjustment(
            n,
            query_lower,
            rs,
            candidate_calories_per100=candidate_calories_per100,
            candidate_protein_per100=candidate_protein_per100,
            candidate_fat_per100=candidate_fat_per100,
            smoked_fish_q=smoked_fish_q,
        )
        score += ff
        reasons.extend(ffr)

    if porridge_like_grain_q:
        pg, pgr = _porridge_like_grain_adjustment(n, query_lower, rs)
        score += pg
        reasons.extend(pgr)

    if is_legume_like and rs in ("cooked", "boiled"):
        le, lr = _legume_cooked_boiled_extra(n, query_lower)
        score += le
        reasons.extend(lr)

    if is_poultry_breast_query:
        pen = _poultry_breast_bad_match(n)
        if pen < 0:
            score += pen
            reasons.append(f"{pen:.0f}:poultry_breast_mismatch")

    if tea_drink_q:
        td, tdr = _tea_drink_row_adjustment(n, ing)
        score += td
        reasons.extend(tdr)

    if cottage_cheese_q:
        cc, cr = _cottage_cheese_adjustment(n, query_lower)
        score += cc
        reasons.extend(cr)

    if banana_fruit_q:
        ba, bar = _banana_fruit_adjustment(n, query_lower, rs)
        score += ba
        reasons.extend(bar)

    if seed_kernel_q:
        sk, skr = _seed_kernel_adjustment(n, query_lower)
        score += sk
        reasons.extend(skr)

    if avocado_like_q or oil_like_q:
        av, avr = _avocado_candidate_adjustment(
            n,
            query_lower,
            avocado_like_q=avocado_like_q,
            oil_like_q=oil_like_q,
            candidate_calories_per100=candidate_calories_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_protein_per100=candidate_protein_per100,
        )
        score += av
        reasons.extend(avr)

    if water_like_q:
        wa, war = _water_candidate_adjustment(
            candidate_name,
            query_lower,
            water_like_q=water_like_q,
            candidate_calories_per100=candidate_calories_per100,
            candidate_carbs_per100=candidate_carbs_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_protein_per100=candidate_protein_per100,
        )
        score += wa
        reasons.extend(war)

    if yogurt_like_q:
        yo, yor = _yogurt_candidate_adjustment(
            candidate_name,
            query_lower,
            yogurt_like_q=yogurt_like_q,
            plain_yogurt_like_q=plain_yogurt_like_q,
            soy_yogurt_like_q=soy_yogurt_like_q,
            candidate_calories_per100=candidate_calories_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_sugar_per100=candidate_sugar_per100,
        )
        score += yo
        reasons.extend(yor)

    if sesame_seed_like_q:
        se, ser = _sesame_seed_candidate_adjustment(
            candidate_name,
            query_lower,
            sesame_seed_like_q=sesame_seed_like_q,
        )
        score += se
        reasons.extend(ser)

    if egg_like_q:
        eg, egr = _egg_candidate_adjustment(
            n,
            query_lower,
            rs,
            egg_like_q=egg_like_q,
            plain_whole_egg_q=plain_whole_egg_q,
            candidate_calories_per100=candidate_calories_per100,
            candidate_protein_per100=candidate_protein_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_carbs_per100=candidate_carbs_per100,
        )
        score += eg
        reasons.extend(egr)

    if passion_fruit_like_q:
        pf, pfr = _passion_fruit_candidate_adjustment(
            n,
            query_lower,
            passion_fruit_like_q=passion_fruit_like_q,
            candidate_calories_per100=candidate_calories_per100,
            candidate_fat_per100=candidate_fat_per100,
        )
        score += pf
        reasons.extend(pfr)

    if crepe_like_q or pancake_like_q:
        cr, crr = _crepe_candidate_adjustment(
            n,
            query_lower,
            crepe_like_q=crepe_like_q,
            pancake_like_q=pancake_like_q,
            candidate_calories_per100=candidate_calories_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_sugar_per100=candidate_sugar_per100,
        )
        score += cr
        reasons.extend(crr)

    if chocolate_truffle_like_q or chocolate_candy_like_q:
        ct, ctr = _chocolate_truffle_candidate_adjustment(
            n,
            query_lower,
            chocolate_truffle_like_q=chocolate_truffle_like_q,
            chocolate_candy_like_q=chocolate_candy_like_q,
            candidate_calories_per100=candidate_calories_per100,
        )
        score += ct
        reasons.extend(ctr)

    if kombucha_like_q:
        kb, kbr = _kombucha_candidate_adjustment(
            candidate_name,
            query_lower,
            kombucha_like_q=kombucha_like_q,
            kombucha_zero_like_q=kombucha_zero_like_q,
            candidate_calories_per100=candidate_calories_per100,
            candidate_protein_per100=candidate_protein_per100,
            candidate_fat_per100=candidate_fat_per100,
            candidate_carbs_per100=candidate_carbs_per100,
            candidate_sugar_per100=candidate_sugar_per100,
            candidate_fiber_per100=candidate_fiber_per100,
        )
        score += kb
        reasons.extend(kbr)

    return score, reasons
