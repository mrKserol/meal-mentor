"""State-aware nutrition matching (requires data/nutrition.csv + data/food_aliases.json)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE_CASES_PATH = _REPO_ROOT / "tests" / "fixtures" / "nutrition_matching_cases.json"

from app.core.config import FOOD_ALIASES_PATH, NUTRITION_CSV_PATH
from app.infrastructure.nutrition.csv_nutrition_provider import NutritionService


def _svc() -> NutritionService | None:
    if not NUTRITION_CSV_PATH or not Path(NUTRITION_CSV_PATH).is_file():
        return None
    return NutritionService(dataset_path=NUTRITION_CSV_PATH, aliases_path=FOOD_ALIASES_PATH)


@pytest.fixture(scope="module")
def nutrition_svc() -> NutritionService:
    svc = _svc()
    if svc is None or not svc.is_available:
        pytest.skip("nutrition.csv not available")
    return svc


def _match(rows: list[dict]) -> str:
    return (list(rows[0].values())[0].get("match") or "").lower()


def test_fried_eggs_alias(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"fried eggs": {"grams": 100, "state": "fried"}})
    data = list(rows[0].values())[0]
    assert data, data
    assert data.get("match") == "Egg, fried, cooked, whole"


def test_white_beans_cooked_not_raw_dry(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"white beans": {"grams": 80, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "boiled" in m or "canned" in m
    assert "raw" not in m
    assert "beans, canned, mature seeds, white" in m or "beans, without salt, boiled" in m


def test_buckwheat_150g_cooked_groats(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"buckwheat": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    assert data.get("match") == "Buckwheat groats, cooked, roasted"


def test_buckwheat_dry_prefers_dry_row(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"buckwheat": {"grams": 100, "state": "dry"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "dry" in m or "uncooked" in m


def test_chicken_breast_fried_meat_only(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"chicken breast": {"grams": 100, "state": "fried"}})
    data = list(rows[0].values())[0]
    assert data
    assert (
        data.get("match")
        == "Chicken, fried, cooked, meat only, breast, broilers or fryers"
    )


def test_rice_cooked(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"rice": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "cooked" in m or "boiled" in m or ("rice" in m and "dry" not in m)


def test_pasta_cooked(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"pasta": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "cooked" in m or "macaroni" in m or ("spaghetti" in m and "dry" not in m)


def test_legacy_numeric(nutrition_svc: NutritionService) -> None:
    agg = nutrition_svc.aggregate_nutrition({"rice": 150})
    assert agg is not None
    assert agg["calories"] >= 0


def test_russian_alias_grechka(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"гречка": {"grams": 180, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    assert "buckwheat" in (data.get("match") or "").lower()


def test_unknown_weird_ingredient_no_crash(nutrition_svc: NutritionService) -> None:
    """Fuzzy search may still pick a row; this only asserts the API does not error."""
    rows = nutrition_svc.search(
        {"zzzznonexistentingredient999_abc": {"grams": 100, "state": "unknown"}}
    )
    assert isinstance(rows, list) and len(rows) == 1
    assert isinstance(list(rows[0].values())[0], dict)


def test_aggregate_full_mixed_format(nutrition_svc: NutritionService) -> None:
    full = nutrition_svc.aggregate_nutrition_full(
        {
            "chicken breast": {"grams": 120, "state": "grilled"},
            "salt": 2,
        }
    )
    assert full is not None
    assert full.get("calories", 0) > 0


def test_prompt_files_salad_rule_and_no_mixed_veg_example() -> None:
    """Prompts must tell the model to split salad veg; examples must not teach 'mixed vegetables'."""
    p1 = (_REPO_ROOT / "data" / "promt.txt").read_text(encoding="utf-8")
    p2 = (_REPO_ROOT / "data" / "promt2.txt").read_text(encoding="utf-8")
    for blob in (p1, p2):
        assert "do NOT use one vague ingredient name" in blob
        assert "mixed vegetables" in blob.lower()
        assert "milk tea" in blob.lower() and "Split into separate" in blob
    assert '"mixed vegetables":' not in p2


def test_milk_tea_not_powder_low_calories(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"milk tea": {"grams": 200, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "powder" not in m and "dry mix" not in m
    assert int(data.get("calories") or 0) < 50


def test_tea_plain_200g_low_calories_brewed_row(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"tea": {"grams": 200, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert int(data.get("calories") or 0) <= 10
    assert "brewed" in m or "prepared with tap water" in m or "prepared with distilled water" in m
    assert "tea" in m
    for bad in ("powder", "dry mix", "instant", "cereal", "dessert", "teaseed"):
        assert bad not in m


def test_cottage_cheese_100g_reasonable_calories(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"cottage cheese": {"grams": 100, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "cottage" in m
    cal = int(data.get("calories") or 0)
    assert 70 <= cal <= 180, f"cottage cheese scaled kcal {cal}"
    for bad in ("cheddar", "cream cheese", "cheesecake", "dessert", "processed"):
        assert bad not in m


def test_banana_80g_raw_calories(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"banana": {"grams": 80, "state": "raw"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "bananas, raw" in m or ("banana" in m and "raw" in m)
    cal = int(data.get("calories") or 0)
    assert 60 <= cal <= 100, f"banana 80g kcal {cal}"
    for bad in ("babyfood", "juice", "beverage", "dessert"):
        assert bad not in m


def test_pumpkin_seeds_10g_dry_calories(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"pumpkin seeds": {"grams": 10, "state": "dry"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "pumpkin" in m and ("seed" in m or "kernels" in m)
    cal = int(data.get("calories") or 0)
    assert 40 <= cal <= 70, f"pumpkin seeds 10g kcal {cal}"
    for bad in ("fish oil", "babyfood", "flour", "meal", "soup", "beverage"):
        assert bad not in m


def test_chia_seeds_5g_dry_calories(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"chia seeds": {"grams": 5, "state": "dry"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "chia" in m
    cal = int(data.get("calories") or 0)
    assert 15 <= cal <= 35, f"chia 5g kcal {cal}"
    for bad in ("babyfood", "beverage"):
        assert bad not in m


def test_nutrition_debug_log_when_env_enabled(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    nutrition_svc: NutritionService,
) -> None:
    monkeypatch.setenv("NUTRITION_DEBUG_MATCHING", "1")
    caplog.set_level(logging.INFO)
    nutrition_svc.search(
        {
            "tea": {"grams": 200, "state": "unknown"},
            "milk tea": {"grams": 100, "state": "unknown"},
        }
    )
    dbg = [r for r in caplog.records if "nutrition_match_debug" in r.message]
    assert len(dbg) >= 2
    assert any("tea" in r.message for r in dbg)


def test_canned_tuna_100g_water_match_and_protein(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"canned tuna": {"grams": 100, "state": "canned"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "tuna" in m and "canned" in m
    assert "drained solids" in m or "in water" in m or "in oil" in m
    for bad in (
        "fish oil",
        "babyfood",
        "salad",
        "soup",
        "sauce",
        "spread",
        "roe",
    ):
        assert bad not in m
    assert "raw" not in m
    cal = int(data.get("calories") or 0)
    assert 80 <= cal <= 180, f"canned tuna (water) calories {cal} expected ~86"
    assert float(data.get("proteins", 0) or 0) >= 18.0


def test_tuna_in_oil_vs_water_calories_and_protein(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    w = nutrition_svc.search({"canned tuna": {"grams": 100, "state": "canned"}})
    o = nutrition_svc.search({"тунец в масле": {"grams": 100, "state": "canned"}})
    dw = list(w[0].values())[0]
    do = list(o[0].values())[0]
    assert dw and do
    assert "oil" in (do.get("match") or "").lower()
    assert int(do.get("calories") or 0) > int(dw.get("calories") or 0)
    assert float(do.get("proteins", 0) or 0) >= 18.0


def test_potato_tuna_onion_combo_macros(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    ing = {
        "canned tuna": {"grams": 100, "state": "canned"},
        "potato": {"grams": 150, "state": "boiled"},
        "onion": {"grams": 30, "state": "raw"},
    }
    full = nutrition_svc.aggregate_nutrition_full(ing)
    assert full is not None
    total_cal = int(round(float(full.get("calories", 0) or 0)))
    total_p = float(full.get("proteins", 0) or 0)
    assert 200 <= total_cal <= 340, f"combo calories {total_cal}"
    assert total_p >= 20.0, f"combo proteins {total_p}"
    flat = flatten_search_results(nutrition_svc.search(ing))
    assert float(flat["canned tuna"].get("proteins", 0) or 0) >= 18.0


def test_coffee_with_milk_not_powder(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"coffee with milk": {"grams": 250, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "powder" not in m
    assert int(data.get("calories") or 0) < 30


def test_boiled_egg_hard_boiled_row(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"boiled egg": {"grams": 120, "state": "boiled"}})
    data = list(rows[0].values())[0]
    assert data.get("match") == "Egg, hard-boiled, cooked, whole"
    assert int(data.get("calories") or 0) >= 160


def test_dates_medjool_raw_coerced_to_dry_calories(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"dates": {"grams": 20, "state": "raw"}})
    data = list(rows[0].values())[0]
    assert data.get("state") == "dry"
    assert data.get("match") in ("Dates, medjool", "Dates, deglet noor")
    assert int(data.get("calories") or 0) >= 45


def test_feta_and_olives_aliases(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    feta = nutrition_svc.search({"feta cheese": {"grams": 50, "state": "raw"}})
    assert "feta" in _match(feta)
    ol = nutrition_svc.search({"olives": {"grams": 30, "state": "canned"}})
    assert "olive" in _match(ol)


def test_shrimp_plain_cooked_not_breaded_or_sauce(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"shrimp": {"grams": 100, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "shrimp" in m
    for bad in ("breaded", "battered", "tempura", "fast food", "sauce", "salad", "soup", "gumbo", "mixture", "dried"):
        assert bad not in m
    cal = int(data.get("calories") or 0)
    assert 70 <= cal <= 130, f"shrimp 100g calories {cal}"
    assert float(data.get("proteins", 0) or 0) >= 18.0
    assert float(data.get("carbohydrates", 0) or 0) <= 5.0


def test_corn_cooked_not_dry_or_flour(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"corn": {"grams": 30, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "corn" in m
    for bad in ("cornmeal", "flour", "starch", "cereal", "snacks", "chips", "popcorn", "dry", "babyfood", "bread", "tortilla"):
        assert bad not in m
    cal = int(data.get("calories") or 0)
    assert 15 <= cal <= 45, f"corn 30g calories {cal}"


def test_shrimp_with_cooked_vegetable_mix_regression(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    ing = {
        "shrimp": {"grams": 100, "state": "cooked"},
        "corn": {"grams": 30, "state": "cooked"},
        "peas": {"grams": 30, "state": "cooked"},
        "green beans": {"grams": 50, "state": "cooked"},
        "carrot": {"grams": 50, "state": "cooked"},
    }
    full = nutrition_svc.aggregate_nutrition_full(ing)
    assert full is not None
    total_cal = int(round(float(full.get("calories", 0) or 0)))
    total_p = float(full.get("proteins", 0) or 0)
    assert 160 <= total_cal <= 320, f"shrimp+veg total calories {total_cal}"
    assert total_p >= 18.0, f"shrimp+veg proteins {total_p}"


def test_beer_regular_not_food_or_mix(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"beer": {"grams": 500, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "beer" in m
    if "alcoholic beverage" in m or "alcoholic beverages" in m:
        assert True
    for bad in ("bread", "batter", "cheese", "soup", "sauce", "snack", "yeast", "dry", "mix", "cereal", "babyfood", "beef", "beet"):
        assert bad not in m
    cal = int(data.get("calories") or 0)
    p = float(data.get("proteins", 0) or 0)
    f = float(data.get("fats", 0) or 0)
    cb = float(data.get("carbohydrates", 0) or 0)
    assert 150 <= cal <= 350, f"beer 500g calories {cal}"
    assert p <= 5.0, f"beer 500g protein {p}"
    assert f <= 2.0, f"beer 500g fat {f}"
    assert cb <= 30.0, f"beer 500g carbs {cb}"


def test_light_beer(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    reg = nutrition_svc.search({"beer": {"grams": 500, "state": "unknown"}})
    lig = nutrition_svc.search({"light beer": {"grams": 500, "state": "unknown"}})
    dr = list(reg[0].values())[0]
    dl = list(lig[0].values())[0]
    assert dr and dl
    assert "beer" in (dl.get("match") or "").lower()
    assert int(dl.get("calories") or 0) <= int(dr.get("calories") or 0)


def test_cooked_grains_fallback_to_oats_not_mix(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"cooked grains": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("oat", "oats", "oatmeal"))
    cal = int(data.get("calories") or 0)
    p = float(data.get("proteins", 0) or 0)
    f = float(data.get("fats", 0) or 0)
    cb = float(data.get("carbohydrates", 0) or 0)
    assert 100 <= cal <= 250, f"cooked grains 150g calories {cal}"
    assert p <= 10.0, f"cooked grains 150g proteins {p}"
    assert f <= 6.0, f"cooked grains 150g fats {f}"
    assert cb >= 15.0, f"cooked grains 150g carbs {cb}"
    for bad in ("protein", "seed", "snack", "bar", "granola", "muesli", "meal replacement", "babyfood", "ready-to-eat", "dry", "uncooked", "unprepared"):
        assert bad not in m


def test_oat_groats_cooked(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"oat groats": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "oat" in m
    cal = int(data.get("calories") or 0)
    p = float(data.get("proteins", 0) or 0)
    f = float(data.get("fats", 0) or 0)
    assert 100 <= cal <= 250, f"oat groats 150g calories {cal}"
    assert p <= 10.0, f"oat groats 150g proteins {p}"
    assert f <= 6.0, f"oat groats 150g fats {f}"


def test_dry_oats_not_cooked(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"dry oats": {"grams": 100, "state": "dry"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "oat" in m
    cal = int(data.get("calories") or 0)
    assert 300 <= cal <= 450, f"dry oats 100g calories {cal}"
    assert "cooked with water" not in m


def test_beef_plain_cooked_not_dish(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"beef": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "beef" in m
    for bad in ("dish", "soup", "mixture", "processed", "canned", "burger"):
        assert bad not in m
    p = float(data.get("proteins", 0) or 0)
    f = float(data.get("fats", 0) or 0)
    cb = float(data.get("carbohydrates", 0) or 0)
    cal = int(data.get("calories") or 0)
    assert p >= 25.0, f"beef 150g proteins {p}"
    assert f <= 30.0, f"beef 150g fats {f}"
    assert cb <= 2.0, f"beef 150g carbs {cb}"
    assert 200 <= cal <= 400, f"beef 150g calories {cal}"


def load_fixture_cases() -> list[dict[str, Any]]:
    raw = json.loads(_FIXTURE_CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("nutrition_matching_cases.json must be a JSON array")
    return raw


def flatten_search_results(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        for k, v in item.items():
            out[k] = v if isinstance(v, dict) else {}
    return out


def get_match_for(results: list[dict[str, Any]], ingredient_name: str) -> str:
    flat = flatten_search_results(results)
    return str(flat.get(ingredient_name, {}).get("match") or "")


def get_state_for(results: list[dict[str, Any]], ingredient_name: str) -> str:
    flat = flatten_search_results(results)
    return str(flat.get(ingredient_name, {}).get("state") or "")


def assert_calories_range(
    aggregate_full: dict[str, Any], expected: dict[str, Any], *, case_name: str
) -> None:
    lo = int(expected["calories_min"])
    hi = int(expected["calories_max"])
    total = int(round(float(aggregate_full.get("calories", 0) or 0)))
    assert lo <= total <= hi, (
        f"{case_name}: calories {total} not in [{lo}, {hi}] "
        f"(aggregate_nutrition_full)"
    )


def assert_required_matches(
    flat: dict[str, dict[str, Any]],
    required: dict[str, str],
    *,
    case_name: str,
) -> None:
    for ing, want in required.items():
        got = str(flat.get(ing, {}).get("match") or "")
        assert got == want, f"{case_name}: {ing!r} expected match {want!r}, got {got!r}"


def assert_allowed_matches(
    flat: dict[str, dict[str, Any]],
    allowed: dict[str, list[str]],
    *,
    case_name: str,
) -> None:
    for ing, options in allowed.items():
        got = str(flat.get(ing, {}).get("match") or "")
        assert got in options, (
            f"{case_name}: {ing!r} match {got!r} not in allowed list {options!r}"
        )


def assert_required_contains_any(
    flat: dict[str, dict[str, Any]],
    spec: dict[str, list[str]],
    *,
    case_name: str,
) -> None:
    for ing, needles in spec.items():
        got = str(flat.get(ing, {}).get("match") or "").lower()
        assert any(n.lower() in got for n in needles), (
            f"{case_name}: {ing!r} match {got!r} must contain one of {needles!r}"
        )


def assert_forbidden_matches(
    flat: dict[str, dict[str, Any]],
    forbidden: dict[str, list[str]],
    *,
    case_name: str,
) -> None:
    for ing, needles in forbidden.items():
        got = str(flat.get(ing, {}).get("match") or "").lower()
        for needle in needles:
            assert needle.lower() not in got, (
                f"{case_name}: {ing!r} match {got!r} must not contain {needle!r}"
            )


def assert_expected_states(
    flat: dict[str, dict[str, Any]],
    states: dict[str, str],
    *,
    case_name: str,
) -> None:
    for ing, want in states.items():
        got = str(flat.get(ing, {}).get("state") or "")
        assert got == want, f"{case_name}: {ing!r} state want {want!r}, got {got!r}"


def assert_match_all_substrings(
    flat: dict[str, dict[str, Any]],
    spec: dict[str, list[str]],
    *,
    case_name: str,
) -> None:
    for ing, needles in spec.items():
        m = str(flat.get(ing, {}).get("match") or "").lower()
        for needle in needles:
            assert needle.lower() in m, (
                f"{case_name}: {ing!r} match must contain {needle!r}, got {m!r}"
            )


def assert_match_any_substrings(
    flat: dict[str, dict[str, Any]],
    spec: dict[str, list[str]],
    *,
    case_name: str,
) -> None:
    for ing, needles in spec.items():
        m = str(flat.get(ing, {}).get("match") or "").lower()
        assert any(n.lower() in m for n in needles), (
            f"{case_name}: {ing!r} match must contain one of {needles!r}, got {m!r}"
        )


def assert_min_aggregate_proteins(
    aggregate_full: dict[str, Any], minimum: float, *, case_name: str
) -> None:
    p = float(aggregate_full.get("proteins", 0) or 0)
    assert p >= minimum, f"{case_name}: aggregate proteins {p} < {minimum}"


def assert_min_scaled_proteins(
    flat: dict[str, dict[str, Any]],
    spec: dict[str, float],
    *,
    case_name: str,
) -> None:
    for ing, minimum in spec.items():
        p = float(flat.get(ing, {}).get("proteins", 0) or 0)
        assert p >= minimum, (
            f"{case_name}: {ing!r} scaled proteins {p} < {minimum}"
        )


def assert_aggregate_macros(
    aggregate_full: dict[str, Any],
    spec: dict[str, Any],
    *,
    case_name: str,
) -> None:
    """spec: { \"proteins\": [min, max], \"fats\": [...], \"carbohydrates\": [...] }"""
    for key, pair in spec.items():
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        lo, hi = float(pair[0]), float(pair[1])
        val = float(aggregate_full.get(key, 0) or 0)
        assert lo <= val <= hi, (
            f"{case_name}: aggregate {key}={val} not in [{lo}, {hi}]"
        )


def assert_max_aggregate_macros(
    aggregate_full: dict[str, Any],
    spec: dict[str, Any],
    *,
    case_name: str,
) -> None:
    for key, maximum in spec.items():
        val = float(aggregate_full.get(key, 0) or 0)
        mx = float(maximum)
        assert val <= mx, f"{case_name}: aggregate {key}={val} > {mx}"


def assert_min_aggregate_macros(
    aggregate_full: dict[str, Any],
    spec: dict[str, Any],
    *,
    case_name: str,
) -> None:
    for key, minimum in spec.items():
        val = float(aggregate_full.get(key, 0) or 0)
        mn = float(minimum)
        assert val >= mn, f"{case_name}: aggregate {key}={val} < {mn}"


def _run_nutrition_case(nutrition_svc: NutritionService, case: dict[str, Any]) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    name = str(case.get("name") or "unnamed")
    ingredients = case.get("ingredients")
    expected = case.get("expected")
    if not isinstance(ingredients, dict) or not isinstance(expected, dict):
        pytest.fail(f"{name}: missing ingredients or expected")

    results = nutrition_svc.search(ingredients, include_candidates=True)
    flat = flatten_search_results(results)
    full = nutrition_svc.aggregate_nutrition_full(ingredients)
    assert full is not None, f"{name}: aggregate_nutrition_full returned None"

    assert_calories_range(full, expected, case_name=name)
    assert_required_matches(flat, expected.get("required_matches") or {}, case_name=name)
    assert_allowed_matches(flat, expected.get("allowed_matches") or {}, case_name=name)
    assert_required_contains_any(
        flat, expected.get("required_contains_any") or {}, case_name=name
    )
    assert_forbidden_matches(
        flat, expected.get("forbidden_match_contains") or {}, case_name=name
    )
    assert_expected_states(flat, expected.get("expected_states") or {}, case_name=name)
    assert_match_all_substrings(
        flat, expected.get("match_all_substrings") or {}, case_name=name
    )
    assert_match_any_substrings(
        flat, expected.get("match_any_substrings") or {}, case_name=name
    )
    if "min_aggregate_proteins" in expected:
        assert_min_aggregate_proteins(
            full, float(expected["min_aggregate_proteins"]), case_name=name
        )
    if "protein_min" in expected:
        assert_min_aggregate_proteins(
            full, float(expected["protein_min"]), case_name=name
        )
    min_macros: dict[str, Any] = {}
    if "protein_min" in expected:
        min_macros["proteins"] = expected["protein_min"]
    if "fat_min" in expected:
        min_macros["fats"] = expected["fat_min"]
    if "carbohydrates_min" in expected:
        min_macros["carbohydrates"] = expected["carbohydrates_min"]
    if min_macros:
        assert_min_aggregate_macros(full, min_macros, case_name=name)
    macros = expected.get("aggregate_macros")
    if isinstance(macros, dict) and macros:
        assert_aggregate_macros(full, macros, case_name=name)
    max_macros: dict[str, Any] = {}
    if "protein_max" in expected:
        max_macros["proteins"] = expected["protein_max"]
    if "fat_max" in expected:
        max_macros["fats"] = expected["fat_max"]
    if "carbohydrates_max" in expected:
        max_macros["carbohydrates"] = expected["carbohydrates_max"]
    if max_macros:
        assert_max_aggregate_macros(full, max_macros, case_name=name)
    assert_min_scaled_proteins(
        flat, expected.get("min_scaled_proteins") or {}, case_name=name
    )


@pytest.mark.parametrize("case", load_fixture_cases(), ids=lambda c: str(c.get("name")))
def test_nutrition_matching_golden_cases(
    nutrition_svc: NutritionService, case: dict[str, Any]
) -> None:
    """Regression cases from tests/fixtures/nutrition_matching_cases.json."""
    _run_nutrition_case(nutrition_svc, case)


def test_golden_breakfast_regression_case(nutrition_svc: NutritionService) -> None:
    """Primary breakfast-style regression: multi-ingredient totals and critical rows."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    case = next(c for c in load_fixture_cases() if c.get("name") == "golden breakfast")
    ingredients = case["ingredients"]
    results = nutrition_svc.search(ingredients, include_candidates=True)
    flat = flatten_search_results(results)
    full = nutrition_svc.aggregate_nutrition_full(ingredients)
    assert full is not None
    total = int(round(float(full.get("calories", 0) or 0)))
    assert 580 <= total <= 680, f"golden breakfast calories {total} not in [580, 680]"

    assert (
        flat["buckwheat"].get("match") == "Buckwheat groats, cooked, roasted"
    ), "buckwheat must be cooked groats, not dry"
    assert "dry" not in (flat["buckwheat"].get("match") or "").lower()
    assert flat["boiled eggs"].get("match") == "Egg, hard-boiled, cooked, whole"
    coffee_match = (flat["coffee"].get("match") or "").lower()
    for bad in ("powder", "dry mix", "milkshake mix", "protein powder"):
        assert bad not in coffee_match, f"coffee match must not suggest {bad!r}"
    dates_cal = int(flat["dates"].get("calories") or 0)
    assert dates_cal >= 40, f"dates scaled calories too low: {dates_cal}"
