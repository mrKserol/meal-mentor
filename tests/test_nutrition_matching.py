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


def test_multilang_ingredient_format_uses_english_key(nutrition_svc: NutritionService) -> None:
    """Extra display fields must not change nutrition lookup for the English key."""
    base = {"rice": {"grams": 100, "state": "cooked"}}
    plain = nutrition_svc.aggregate_nutrition(base)
    with_display = nutrition_svc.aggregate_nutrition(
        {
            "rice": {
                "grams": 100,
                "state": "cooked",
                "name_translated": "рис",
                "name_language": "ru",
            }
        }
    )
    assert plain is not None and with_display is not None
    assert plain["calories"] == with_display["calories"]


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


def test_text_prompt_multilang_fields() -> None:
    p2 = (_REPO_ROOT / "data" / "promt2.txt").read_text(encoding="utf-8")
    assert "prediction_translated" in p2
    assert "name_translated" in p2
    assert '"prediction": "Short English base dish name"' in p2


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
    for bad in ("dish", "soup", "mixture", "processed", "canned", "burger", "babyfood", "sauce", "potato", "rice", "pasta"):
        assert bad not in m
    p = float(data.get("proteins", 0) or 0)
    f = float(data.get("fats", 0) or 0)
    cb = float(data.get("carbohydrates", 0) or 0)
    cal = int(data.get("calories") or 0)
    assert p >= 25.0, f"beef 150g proteins {p}"
    assert f <= 35.0, f"beef 150g fats {f}"
    assert cb <= 2.0, f"beef 150g carbs {cb}"
    assert 200 <= cal <= 400, f"beef 150g calories {cal}"


def test_beef_patty_not_fat(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"beef patty": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "beef" in m
    assert "patty" in m or "ground" in m
    for bad in ("fat", "tallow", "suet", "separable fat", "fat only", "babyfood", "sausage", "canned"):
        assert bad not in m
    cal = int(data.get("calories") or 0)
    p = float(data.get("proteins", 0) or 0)
    f = float(data.get("fats", 0) or 0)
    cb = float(data.get("carbohydrates", 0) or 0)
    assert 300 <= cal <= 550, f"beef patty 150g calories {cal}"
    assert p >= 25.0, f"beef patty 150g proteins {p}"
    assert 15.0 <= f <= 45.0, f"beef patty 150g fats {f}"
    assert cb <= 5.0, f"beef patty 150g carbs {cb}"


def _assert_zero_cola_match(data: dict[str, Any], *, label: str) -> None:
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("low calorie", "diet", "cola", "carbonated")), (
        f"{label}: match {m!r} must be diet/low-calorie cola"
    )
    for bad in (
        "oil",
        "fat",
        "butter",
        "syrup",
        "regular",
        "sweetened",
        "dessert",
        "sauce",
        "powder",
        "dry mix",
    ):
        assert bad not in m, f"{label}: match must not contain {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    p = float(data.get("proteins") or 0)
    f = float(data.get("fats") or 0)
    cb = float(data.get("carbohydrates") or 0)
    assert cal <= 10, f"{label}: calories {cal}"
    assert p <= 1.0, f"{label}: proteins {p}"
    assert f <= 0.5, f"{label}: fats {f}"
    assert cb <= 2.0, f"{label}: carbs {cb}"


def test_coca_cola_zero_ru_case_insensitive(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"Кока-Кола Зеро": {"grams": 320, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    _assert_zero_cola_match(data, label="Кока-Кола Зеро")


def test_coca_cola_zero_ru_lowercase_hyphen(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"Кока-кола зеро": {"grams": 320, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    _assert_zero_cola_match(data, label="Кока-кола зеро")


def test_coca_cola_zero_ru_no_hyphen(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"кока кола зеро": {"grams": 320, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    _assert_zero_cola_match(data, label="кока кола зеро")


def test_coke_zero_en(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"Coke Zero": {"grams": 320, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    _assert_zero_cola_match(data, label="Coke Zero")


def test_regular_cola_not_zero(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"Coca-Cola": {"grams": 320, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "low calorie" not in m and "diet" not in m, f"regular cola matched diet row: {m!r}"
    for bad in ("oil", "fat", "butter"):
        assert bad not in m
    cal = int(data.get("calories") or 0)
    cb = float(data.get("carbohydrates") or 0)
    assert 120 <= cal <= 160, f"regular cola 320g calories {cal}"
    assert 30.0 <= cb <= 45.0, f"regular cola 320g carbs {cb}"


def _assert_coconut_water_match(data: dict[str, Any], *, label: str) -> None:
    m = (data.get("match") or "").lower()
    assert any(
        x in m for x in ("coconut water", "liquid from coconuts", "beverage")
    ), f"{label}: match {m!r} must be coconut water beverage"
    for bad in (
        "oil",
        "coconut oil",
        "coconut meat",
        "raw coconut",
        "dried coconut",
        "desiccated",
        "coconut milk",
        "coconut cream",
        "flour",
        "butter",
    ):
        assert bad not in m, f"{label}: match must not contain {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    p = float(data.get("proteins") or 0)
    f = float(data.get("fats") or 0)
    cb = float(data.get("carbohydrates") or 0)
    fiber = float(data.get("fiber_g") or data.get("fiber") or 0)
    assert 40 <= cal <= 120, f"{label}: calories {cal}"
    assert p <= 3.0, f"{label}: proteins {p}"
    assert f <= 2.0, f"{label}: fats {f}"
    assert 8.0 <= cb <= 30.0, f"{label}: carbs {cb}"
    assert fiber <= 2.0, f"{label}: fiber {fiber}"


def test_coconut_water_not_coconut_meat(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"coconut water": {"grams": 400, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    _assert_coconut_water_match(data, label="coconut water")


def test_coconut_water_ru(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"кокосовая вода": {"grams": 400, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    _assert_coconut_water_match(data, label="кокосовая вода")


def test_coconut_meat_still_high_calorie(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"coconut meat": {"grams": 100, "state": "raw"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "coconut" in m
    assert "water" not in m
    cal = int(data.get("calories") or 0)
    f = float(data.get("fats") or 0)
    assert cal > 250, f"coconut meat 100g calories {cal}"
    assert f > 20.0, f"coconut meat 100g fats {f}"


def test_coconut_milk_not_water(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"coconut milk": {"grams": 100, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "coconut milk" in m or ("coconut" in m and "milk" in m)
    assert "coconut water" not in m and "liquid from coconuts" not in m


def test_normalize_alias_key_coca_zero_variants() -> None:
    from app.infrastructure.nutrition.food_aliases import normalize_alias_key

    keys = {
        normalize_alias_key("Кока-Кола Зеро"),
        normalize_alias_key("Кока-кола зеро"),
        normalize_alias_key("кока кола зеро"),
        normalize_alias_key("Кока—кола зеро"),
    }
    assert keys == {"кока кола зеро"}


def test_borscht_not_fat_or_dry_mix(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"borscht": {"grams": 300, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("soup", "borscht", "borsch", "beet", "vegetable"))
    for bad in (
        "dry mix",
        "dehydrated",
        "powder",
        "sauce",
        "gravy",
        "oil",
        "fat",
        "shortening",
        "babyfood",
    ):
        assert bad not in m, f"borscht matched bad row: {m!r}"
    cal = int(data.get("calories") or 0)
    f = float(data.get("fats") or 0)
    assert 80 <= cal <= 350, f"borscht 300g calories {cal}"
    assert f <= 18.0, f"borscht 300g fats {f}"


def test_borscht_with_bread_regression(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    ingredients = {
        "borscht": {"grams": 300, "state": "cooked"},
        "bread": {"grams": 50, "state": "unknown"},
    }
    full = nutrition_svc.aggregate_nutrition_full(ingredients)
    assert full is not None
    cal = int(round(float(full.get("calories", 0) or 0)))
    p = float(full.get("proteins", 0) or 0)
    f = float(full.get("fats", 0) or 0)
    cb = float(full.get("carbohydrates", 0) or 0)
    assert 180 <= cal <= 500, f"borscht+bread calories {cal}"
    assert f <= 20.0, f"borscht+bread fats {f}"
    assert 30.0 <= cb <= 75.0, f"borscht+bread carbs {cb}"
    rows = nutrition_svc.search(ingredients)
    m = (list(rows[0].values())[0].get("match") or "").lower()
    for bad in ("dry mix", "dehydrated", "powder", "sauce", "gravy", "oil", "fat", "shortening"):
        assert bad not in m, f"borscht matched bad row: {m!r}"
    assert p >= 6.0, f"borscht+bread proteins {p}"


def test_generic_soup_not_dry_mix(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"soup": {"grams": 300, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    for bad in ("dry mix", "dehydrated", "powder", "oil", "fat", "gravy", "shortening"):
        assert bad not in m, f"soup matched bad row: {m!r}"
    cal = int(data.get("calories") or 0)
    assert 60 <= cal <= 450, f"soup 300g calories {cal}"


def test_lentil_soup_not_dry_mix(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"lentil soup": {"grams": 300, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    for bad in ("dry mix", "dehydrated", "powder", "oil", "fat", "gravy"):
        assert bad not in m, f"lentil soup matched bad row: {m!r}"
    cal = int(data.get("calories") or 0)
    p = float(data.get("proteins") or 0)
    assert 60 <= cal <= 400, f"lentil soup 300g calories {cal}"
    assert p >= 5.0, f"lentil soup 300g proteins {p}"


def test_smoked_fish_not_fish_oil(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"smoked fish": {"grams": 100, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    for bad in (
        "oil",
        "fish oil",
        "cod liver oil",
        "sauce",
        "soup",
        "spread",
        "babyfood",
        "roe",
    ):
        assert bad not in m, f"smoked fish matched bad row: {m!r}"
    cal = int(data.get("calories") or 0)
    p = float(data.get("proteins") or 0)
    f = float(data.get("fats") or 0)
    cb = float(data.get("carbohydrates") or 0)
    assert 100 <= cal <= 350, f"smoked fish 100g calories {cal}"
    assert p >= 10.0, f"smoked fish 100g proteins {p}"
    assert f <= 30.0, f"smoked fish 100g fats {f}"
    assert cb <= 2.0, f"smoked fish 100g carbs {cb}"


def test_smoked_fish_meal_regression(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    ingredients = {
        "smoked fish": {"grams": 100, "state": "unknown"},
        "potato": {"grams": 50, "state": "boiled"},
        "sauerkraut": {"grams": 40, "state": "canned"},
    }
    rows = nutrition_svc.search(ingredients, include_candidates=True)
    flat = flatten_search_results(rows)
    full = nutrition_svc.aggregate_nutrition_full(ingredients)
    assert full is not None
    cal = int(full.get("calories") or 0)
    p = float(full.get("proteins") or 0)
    f = float(full.get("fats") or 0)
    assert 180 <= cal <= 430, f"meal calories {cal}"
    assert p >= 12.0, f"meal proteins {p}"
    assert f <= 30.0, f"meal fats {f}"
    sf = str(flat.get("smoked fish", {}).get("match") or "").lower()
    for bad in ("oil", "fish oil", "cod liver oil", "fat only"):
        assert bad not in sf, f"smoked fish match {sf!r}"


def test_millet_porridge_plain_weight_not_dry(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"millet porridge": 150})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "millet" in m
    assert "cooked" in m
    for bad in ("raw", "flour", "puffed", "unprepared", "uncooked"):
        assert bad not in m
    cal = int(data.get("calories") or 0)
    assert 120 <= cal <= 280, f"millet porridge 150g plain weight calories {cal}"


def test_cornmeal_porridge_cooked_not_dry(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"cornmeal porridge": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("corn", "grits", "polenta", "cereal"))
    for bad in ("dry", "flour", "starch", "dry mix", "ready-to-eat", "bread", "muffin", "pancake", "snack", "unprepared", "uncooked"):
        assert bad not in m
    cal = int(data.get("calories") or 0)
    p = float(data.get("proteins", 0) or 0)
    f = float(data.get("fats", 0) or 0)
    cb = float(data.get("carbohydrates", 0) or 0)
    assert 80 <= cal <= 220, f"cornmeal porridge 150g calories {cal}"
    assert p <= 8.0, f"cornmeal porridge 150g proteins {p}"
    assert f <= 8.0, f"cornmeal porridge 150g fats {f}"
    assert 15.0 <= cb <= 45.0, f"cornmeal porridge 150g carbs {cb}"


def test_breakfast_cornmeal_porridge_regression(nutrition_svc: NutritionService) -> None:
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    ing = {
        "boiled eggs": {"grams": 120, "state": "boiled"},
        "strawberries": {"grams": 100, "state": "raw"},
        "almonds": {"grams": 30, "state": "raw"},
        "chocolate truffle": {"grams": 15, "state": "unknown"},
        "cornmeal porridge": {"grams": 150, "state": "cooked"},
        "tea": {"grams": 150, "state": "unknown"},
        "milk": {"grams": 50, "state": "unknown"},
    }
    full = nutrition_svc.aggregate_nutrition_full(ing)
    assert full is not None
    total_cal = int(round(float(full.get("calories", 0) or 0)))
    total_p = float(full.get("proteins", 0) or 0)
    total_f = float(full.get("fats", 0) or 0)
    total_c = float(full.get("carbohydrates", 0) or 0)
    assert 500 <= total_cal <= 750, f"breakfast cornmeal porridge calories {total_cal}"
    assert total_p >= 20.0, f"breakfast cornmeal porridge proteins {total_p}"
    assert total_f >= 20.0, f"breakfast cornmeal porridge fats {total_f}"
    assert 45.0 <= total_c <= 95.0, f"breakfast cornmeal porridge carbs {total_c}"
    flat = flatten_search_results(nutrition_svc.search(ing))
    cm = str(flat.get("cornmeal porridge", {}).get("match") or "").lower()
    assert any(x in cm for x in ("corn", "grits", "polenta", "cereal"))
    for bad in ("dry", "flour", "starch", "unprepared", "uncooked"):
        assert bad not in cm
    tea_match = str(flat.get("tea", {}).get("match") or "").lower()
    for bad in ("powder", "dry mix", "instant", "milkshake mix", "protein powder"):
        assert bad not in tea_match


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
    if "fiber_max" in expected:
        max_macros["fiber_g"] = expected["fiber_max"]
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


def test_water_not_watermelon(nutrition_svc: NutritionService) -> None:
    """Plain 'water' must match a water row, not watermelon."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"water": {"grams": 500, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    cal = int(data.get("calories") or 0)
    assert cal <= 2, f"water 500g should have <=2 kcal, got {cal}; match={m!r}"
    assert "water" in m, f"water match must contain 'water', got {m!r}"
    for bad in ("watermelon", "coconut", "juice", "soda", "soup", "oil", "fat"):
        assert bad not in m, f"water match must not contain {bad!r}, got {m!r}"


def test_water_ru_not_watermelon(nutrition_svc: NutritionService) -> None:
    """Russian 'вода' must match a water row, not watermelon."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"вода": {"grams": 500, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    cal = int(data.get("calories") or 0)
    assert cal <= 2, f"вода 500g should have <=2 kcal, got {cal}; match={m!r}"
    assert "water" in m, f"вода match must contain 'water', got {m!r}"
    for bad in ("watermelon", "coconut", "juice", "soda", "soup", "oil", "fat"):
        assert bad not in m, f"вода match must not contain {bad!r}, got {m!r}"


def test_plain_yogurt_not_silk_peach_soy(nutrition_svc: NutritionService) -> None:
    """Plain 'yogurt' must not match SILK/peach/soy/flavored yogurt."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"yogurt": {"grams": 100, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    cal = int(data.get("calories") or 0)
    assert 40 <= cal <= 130, f"plain yogurt 100g calories {cal} expected 40–130; match={m!r}"
    for bad in ("silk", "peach", "soy", "flavored", "frozen", "dessert"):
        assert bad not in m, f"plain yogurt must not match {bad!r}, got {m!r}"


def test_yogurt_ru_plain(nutrition_svc: NutritionService) -> None:
    """Russian 'йогурт' must not match SILK/peach/soy/flavored yogurt."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"йогурт": {"grams": 100, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    cal = int(data.get("calories") or 0)
    assert 40 <= cal <= 130, f"йогурт 100g calories {cal} expected 40–130; match={m!r}"
    for bad in ("silk", "peach", "soy", "flavored", "frozen", "dessert"):
        assert bad not in m, f"йогурт must not match {bad!r}, got {m!r}"


def test_soy_yogurt_when_explicit(nutrition_svc: NutritionService) -> None:
    """Explicit 'soy yogurt' should match a soy-based yogurt row."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"soy yogurt": {"grams": 100, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "soy" in m or "silk" in m, f"soy yogurt must contain 'soy' or 'silk', got {m!r}"


def test_white_sesame_seeds_not_cheese(nutrition_svc: NutritionService) -> None:
    """White sesame seeds must not match cheese/queso/beans/mothbeans."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"white sesame seeds": {"grams": 5, "state": "dry"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    cal = int(data.get("calories") or 0)
    assert "sesame" in m, f"white sesame seeds must contain 'sesame', got {m!r}"
    assert 20 <= cal <= 40, f"white sesame seeds 5g calories {cal} expected 20–40; match={m!r}"
    for bad in ("cheese", "queso", "beans", "mothbeans", "mature seeds"):
        assert bad not in m, f"white sesame seeds must not match {bad!r}, got {m!r}"


def test_black_sesame_seeds_not_mothbeans(nutrition_svc: NutritionService) -> None:
    """Black sesame seeds must not match cheese/beans/mothbeans."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"black sesame seeds": {"grams": 5, "state": "dry"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    cal = int(data.get("calories") or 0)
    assert "sesame" in m, f"black sesame seeds must contain 'sesame', got {m!r}"
    assert 20 <= cal <= 40, f"black sesame seeds 5g calories {cal} expected 20–40; match={m!r}"
    for bad in ("cheese", "queso", "beans", "mothbeans", "mature seeds"):
        assert bad not in m, f"black sesame seeds must not match {bad!r}, got {m!r}"


def test_avocado_not_avocado_oil(nutrition_svc: NutritionService) -> None:
    """Avocado should match raw avocado flesh, not Oil, avocado."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"avocado": {"grams": 75, "state": "raw"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    # Must contain avocado and either raw or avocados
    assert "avocado" in m, f"avocado match must contain 'avocado', got {m!r}"
    assert "raw" in m or "avocados" in m, f"avocado match must contain 'raw' or 'avocados', got {m!r}"
    # Must not be oil or processed forms
    for bad in ("oil", "dressing", "sauce", "babyfood", "powder"):
        assert bad not in m, f"avocado match must not contain {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    fat = float(data.get("fats") or 0)
    carbs = float(data.get("carbohydrates") or 0)
    fiber = float(data.get("fiber_g") or 0)
    assert 90 <= cal <= 160, f"avocado 75g calories {cal} expected 90–160"
    assert 8 <= fat <= 18, f"avocado 75g fat {fat} expected 8–18"
    assert 3 <= carbs <= 10, f"avocado 75g carbs {carbs} expected 3–10"
    assert fiber >= 3, f"avocado 75g fiber {fiber} expected >= 3"


def test_avocado_ru_not_oil(nutrition_svc: NutritionService) -> None:
    """Russian 'авокадо' must not match avocado oil."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"авокадо": {"grams": 75, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "avocado" in m, f"авокадо match must contain 'avocado', got {m!r}"
    assert "raw" in m or "avocados" in m, f"авокадо match must contain 'raw' or 'avocados', got {m!r}"
    for bad in ("oil", "dressing", "sauce", "babyfood", "powder"):
        assert bad not in m, f"авокадо match must not contain {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    fat = float(data.get("fats") or 0)
    assert 90 <= cal <= 160, f"авокадо 75g calories {cal} expected 90–160"
    assert 8 <= fat <= 18, f"авокадо 75g fat {fat} expected 8–18"


def test_avocado_oil_still_oil(nutrition_svc: NutritionService) -> None:
    """'avocado oil' must match the oil row, not raw avocado."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"avocado oil": {"grams": 10, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "oil" in m, f"avocado oil match must contain 'oil', got {m!r}"
    cal = int(data.get("calories") or 0)
    fat = float(data.get("fats") or 0)
    carbs = float(data.get("carbohydrates") or 0)
    assert 80 <= cal <= 100, f"avocado oil 10g calories {cal} expected 80–100"
    assert fat >= 9, f"avocado oil 10g fat {fat} expected >= 9"
    assert carbs <= 1, f"avocado oil 10g carbs {carbs} expected <= 1"


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


# --- Egg matching tests ---

def test_boiled_egg_not_potato_salad(nutrition_svc: NutritionService) -> None:
    """Plain 'egg' boiled should not match potato salad with egg or other compound dishes."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"egg": {"grams": 150, "state": "boiled"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    # Must contain egg and one of: hard-boiled, boiled, cooked, whole
    assert "egg" in m, f"egg match must contain 'egg', got {m!r}"
    assert any(x in m for x in ("hard-boiled", "boiled", "cooked", "whole")), (
        f"egg match must contain hard-boiled/boiled/cooked/whole, got {m!r}"
    )
    # Must not be compound dish
    for bad in ("potato salad", "salad", "sandwich", "burrito", "fast food", "babyfood", "mayonnaise", "sauce"):
        assert bad not in m, f"egg must not match {bad!r}, got {m!r}"
    # Macro checks (for 150g)
    cal = int(data.get("calories") or 0)
    prot = float(data.get("proteins") or 0)
    fat = float(data.get("fats") or 0)
    carb = float(data.get("carbohydrates") or 0)
    assert 190 <= cal <= 270, f"egg 150g boiled calories {cal} expected 190–270"
    assert prot >= 15.0, f"egg 150g boiled protein {prot} expected >= 15"
    assert 10.0 <= fat <= 22.0, f"egg 150g boiled fat {fat} expected 10–22"
    assert carb <= 5.0, f"egg 150g boiled carbs {carb} expected <= 5"


def test_boiled_egg_ru_not_potato_salad(nutrition_svc: NutritionService) -> None:
    """Russian 'яйцо' boiled should not match potato salad or other compound dishes."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"яйцо": {"grams": 150, "state": "boiled"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "egg" in m, f"яйцо match must contain 'egg', got {m!r}"
    assert any(x in m for x in ("hard-boiled", "boiled", "cooked", "whole")), (
        f"яйцо match must contain hard-boiled/boiled/cooked/whole, got {m!r}"
    )
    for bad in ("potato salad", "salad", "sandwich", "burrito", "fast food", "babyfood", "mayonnaise", "sauce"):
        assert bad not in m, f"яйцо must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    prot = float(data.get("proteins") or 0)
    fat = float(data.get("fats") or 0)
    carb = float(data.get("carbohydrates") or 0)
    assert 190 <= cal <= 270, f"яйцо 150g boiled calories {cal} expected 190–270"
    assert prot >= 15.0, f"яйцо 150g boiled protein {prot} expected >= 15"
    assert 10.0 <= fat <= 22.0, f"яйцо 150g boiled fat {fat} expected 10–22"
    assert carb <= 5.0, f"яйцо 150g boiled carbs {carb} expected <= 5"


def _check_beef_steak_match(data: dict[str, Any], *, label: str) -> None:
    """Assert that a beef steak match is a cooked/grilled steak row, not tallow/fat."""
    import re as _re
    m = (data.get("match") or "").lower()
    # Must contain beef and steak-like cut
    assert "beef" in m, f"{label}: match must contain 'beef', got {m!r}"
    assert any(x in m for x in ("steak", "sirloin", "ribeye", "rib eye", "tenderloin", "loin", "round")), (
        f"{label}: match must contain a steak-related word, got {m!r}"
    )
    # Must not be fat/tallow/bad rows (use word-boundary checks for ambiguous words)
    for bad in ("tallow", "beef fat", "separable fat", "fat only", "suet", "lard", "sausage", "burger", "patty", "canned", "babyfood"):
        assert bad not in m, f"{label}: match must not contain {bad!r}, got {m!r}"
    # "oil" check: must not contain " oil" as standalone word (not in "broiled")
    assert not _re.search(r"\boil\b", m), f"{label}: match must not contain 'oil' as word, got {m!r}"
    cal = int(data.get("calories") or 0)
    p = float(data.get("proteins") or 0)
    fat = float(data.get("fats") or 0)
    cb = float(data.get("carbohydrates") or 0)
    assert 170 <= cal <= 350, f"{label}: 100g calories {cal} expected 170–350"
    assert p >= 20.0, f"{label}: 100g protein {p} expected >= 20"
    assert 5.0 <= fat <= 30.0, f"{label}: 100g fat {fat} expected 5–30"
    assert cb <= 2.0, f"{label}: 100g carbs {cb} expected <= 2"


def test_beef_steak_grilled_not_tallow(nutrition_svc: NutritionService) -> None:
    """Grilled beef steak must not match beef tallow or fat-only rows."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"beef steak": {"grams": 100, "state": "grilled"}})
    data = list(rows[0].values())[0]
    assert data
    _check_beef_steak_match(data, label="beef steak 100g grilled")


def test_beef_steak_ru_grilled_not_tallow(nutrition_svc: NutritionService) -> None:
    """Russian говяжий стейк must not match beef tallow or fat-only rows."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"говяжий стейк": {"grams": 100, "state": "grilled"}})
    data = list(rows[0].values())[0]
    assert data
    _check_beef_steak_match(data, label="говяжий стейк 100g grilled")


def test_beef_tallow_still_allowed_when_explicit(nutrition_svc: NutritionService) -> None:
    """Explicit 'beef tallow' should still match the tallow row."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"beef tallow": {"grams": 10, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("tallow", "fat")), f"beef tallow must match tallow/fat row, got {m!r}"
    cal = int(data.get("calories") or 0)
    f = float(data.get("fats") or 0)
    assert 80 <= cal <= 100, f"beef tallow 10g calories {cal} expected 80–100"
    assert f >= 9.0, f"beef tallow 10g fat {f} expected >= 9"


def test_egg_salad_can_match_non_plain_when_explicit(nutrition_svc: NutritionService) -> None:
    """Explicit 'egg salad' query should not be forced to match plain hard-boiled egg."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"egg salad": {"grams": 150, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    # Should contain egg — but allowed to match various egg preparations
    assert "egg" in m, f"egg salad match must contain 'egg', got {m!r}"
    # Must not match obviously unrelated items
    for bad in ("eggnog", "eggplant", "babyfood"):
        assert bad not in m, f"egg salad must not match {bad!r}, got {m!r}"


# ===== Passion fruit tests =====

def test_passion_fruit_not_juice_drink(nutrition_svc: NutritionService) -> None:
    """passion fruit 50g raw must match raw fruit, not beverage/juice/drink/V8/SPLASH."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"passion fruit": {"grams": 50, "state": "raw"}})
    data = list(rows[0].values())[0]
    assert data, "passion fruit 50g raw: no match found"
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("passion", "granadilla")), (
        f"passion fruit match must contain passion/granadilla, got {m!r}"
    )
    for bad in ("beverage", "juice", "drink", "v8", "splash", "nectar", "syrup"):
        assert bad not in m, f"passion fruit must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    assert 20 <= cal <= 60, f"passion fruit 50g calories {cal} expected 20–60"


def test_passion_fruit_ru_not_juice_drink(nutrition_svc: NutritionService) -> None:
    """Russian маракуйя 50g raw must match raw fruit, not beverage/juice/drink."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"маракуйя": {"grams": 50, "state": "raw"}})
    data = list(rows[0].values())[0]
    assert data, "маракуйя 50g raw: no match found"
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("passion", "granadilla")), (
        f"маракуйя match must contain passion/granadilla, got {m!r}"
    )
    for bad in ("beverage", "juice", "drink", "v8", "splash", "nectar", "syrup"):
        assert bad not in m, f"маракуйя must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    assert 20 <= cal <= 60, f"маракуйя 50g calories {cal} expected 20–60"


# ===== Crepe tests =====

def test_crepes_not_cookies(nutrition_svc: NutritionService) -> None:
    """crepes 150g cooked must match cooked crepe/pancake, not KEEBLER/cookie."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"crepes": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data, "crepes 150g cooked: no match found"
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("crepe", "pancake")), (
        f"crepes match must contain crepe/pancake, got {m!r}"
    )
    for bad in ("keebler", "cookie", "cookies", "sweet cremes", "cracker", "wafer", "cereal"):
        assert bad not in m, f"crepes must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    assert 200 <= cal <= 450, f"crepes 150g calories {cal} expected 200–450"
    carbs = float(data.get("carbohydrates") or 0)
    assert carbs >= 25, f"crepes 150g carbs {carbs} expected >= 25"


def test_crepes_ru_not_cookies(nutrition_svc: NutritionService) -> None:
    """Russian блины 150g cooked must match cooked crepe/pancake, not KEEBLER/cookie."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"блины": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data, "блины 150g cooked: no match found"
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("crepe", "pancake")), (
        f"блины match must contain crepe/pancake, got {m!r}"
    )
    for bad in ("keebler", "cookie", "cookies", "sweet cremes", "cracker", "wafer", "cereal"):
        assert bad not in m, f"блины must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    assert 200 <= cal <= 450, f"блины 150g calories {cal} expected 200–450"
    carbs = float(data.get("carbohydrates") or 0)
    assert carbs >= 25, f"блины 150g carbs {carbs} expected >= 25"


# ===== Chocolate truffle tests =====

def test_chocolate_truffle_not_syrup(nutrition_svc: NutritionService) -> None:
    """chocolate truffle 15g must match chocolate candy, not syrup/fudge-type/sauce."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"chocolate truffle": {"grams": 15, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data, "chocolate truffle 15g: no match found"
    m = (data.get("match") or "").lower()
    assert "chocolate" in m, f"chocolate truffle match must contain 'chocolate', got {m!r}"
    assert any(x in m for x in ("truffle", "candy", "candies", "confectionery")), (
        f"chocolate truffle match must contain truffle/candy/candies/confectionery, got {m!r}"
    )
    for bad in ("syrup", "fudge-type", "sauce", "topping", "powder", "beverage", "baking"):
        assert bad not in m, f"chocolate truffle must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    assert 50 <= cal <= 120, f"chocolate truffle 15g calories {cal} expected 50–120"
    fat = float(data.get("fats") or 0)
    assert 2 <= fat <= 9, f"chocolate truffle 15g fat {fat} expected 2–9"
    carbs = float(data.get("carbohydrates") or 0)
    assert 4 <= carbs <= 15, f"chocolate truffle 15g carbs {carbs} expected 4–15"


def test_chocolate_truffle_ru_not_syrup(nutrition_svc: NutritionService) -> None:
    """Russian шоколадный трюфель 15g must match chocolate candy, not syrup/sauce."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"шоколадный трюфель": {"grams": 15, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data, "шоколадный трюфель 15g: no match found"
    m = (data.get("match") or "").lower()
    assert "chocolate" in m, f"шоколадный трюфель match must contain 'chocolate', got {m!r}"
    assert any(x in m for x in ("truffle", "candy", "candies", "confectionery")), (
        f"шоколадный трюфель match must contain truffle/candy/candies/confectionery, got {m!r}"
    )
    for bad in ("syrup", "fudge-type", "sauce", "topping", "powder", "beverage", "baking"):
        assert bad not in m, f"шоколадный трюфель must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    assert 50 <= cal <= 120, f"шоколадный трюфель 15g calories {cal} expected 50–120"
    fat = float(data.get("fats") or 0)
    assert 2 <= fat <= 9, f"шоколадный трюфель 15g fat {fat} expected 2–9"
    carbs = float(data.get("carbohydrates") or 0)
    assert 4 <= carbs <= 15, f"шоколадный трюфель 15g carbs {carbs} expected 4–15"


# ===== Kombucha tests =====

def test_kombucha_not_buckwheat(nutrition_svc: NutritionService) -> None:
    """kombucha 330g unknown must match tea/beverage, not buckwheat/grain."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"kombucha": {"grams": 330, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data, "kombucha 330g: no match found"
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("tea", "beverage", "drink")), (
        f"kombucha match must contain tea/beverage/drink, got {m!r}"
    )
    for bad in ("buckwheat", "groats", "cereal", "grain", "flour", "raw mango", "kiwi fruit"):
        assert bad not in m, f"kombucha must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    assert 0 <= cal <= 120, f"kombucha 330g calories {cal} expected 0–120"
    prot = float(data.get("proteins") or 0)
    assert prot <= 2, f"kombucha 330g protein {prot} expected <= 2"
    fat = float(data.get("fats") or 0)
    assert fat <= 1, f"kombucha 330g fat {fat} expected <= 1"
    carbs = float(data.get("carbohydrates") or 0)
    assert carbs <= 30, f"kombucha 330g carbs {carbs} expected <= 30"


def test_kombucha_ru_not_buckwheat(nutrition_svc: NutritionService) -> None:
    """Russian комбуча 330g unknown must match tea/beverage, not buckwheat/grain."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"комбуча": {"grams": 330, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data, "комбуча 330g: no match found"
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("tea", "beverage", "drink")), (
        f"комбуча match must contain tea/beverage/drink, got {m!r}"
    )
    for bad in ("buckwheat", "groats", "cereal", "grain", "flour", "dry"):
        assert bad not in m, f"комбуча must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    assert 0 <= cal <= 120, f"комбуча 330g calories {cal} expected 0–120"
    prot = float(data.get("proteins") or 0)
    assert prot <= 2, f"комбуча 330g protein {prot} expected <= 2"
    fat = float(data.get("fats") or 0)
    assert fat <= 1, f"комбуча 330g fat {fat} expected <= 1"
    carbs = float(data.get("carbohydrates") or 0)
    assert carbs <= 30, f"комбуча 330g carbs {carbs} expected <= 30"


def test_kombucha_mango_kiwi_flavor_not_fruit(nutrition_svc: NutritionService) -> None:
    """Flavored kombucha must match beverage, not raw mango/kiwi or buckwheat."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"комбуча со вкусом манго и киви": {"grams": 330, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data, "комбуча со вкусом манго и киви 330g: no match found"
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("tea", "beverage", "drink")), (
        f"комбуча манго киви match must contain tea/beverage/drink, got {m!r}"
    )
    for bad in ("buckwheat", "groats", "cereal", "grain", "flour", "raw mango", "kiwi fruit", "mango, raw"):
        assert bad not in m, f"комбуча манго киви must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    assert cal <= 120, f"комбуча манго киви 330g calories {cal} expected <= 120"


def test_zero_sugar_kombucha(nutrition_svc: NutritionService) -> None:
    """Sugar-free kombucha must match low-calorie tea/beverage row, not grain."""
    if not nutrition_svc.aliases.is_loaded:
        pytest.skip("food_aliases.json not loaded")
    rows = nutrition_svc.search({"комбуча без сахара": {"grams": 330, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data, "комбуча без сахара 330g: no match found"
    m = (data.get("match") or "").lower()
    assert any(x in m for x in ("tea", "beverage", "drink")), (
        f"комбуча без сахара match must contain tea/beverage/drink, got {m!r}"
    )
    for bad in ("buckwheat", "groats", "cereal", "grain", "flour"):
        assert bad not in m, f"комбуча без сахара must not match {bad!r}, got {m!r}"
    cal = int(data.get("calories") or 0)
    assert cal <= 120, f"комбуча без сахара 330g calories {cal} expected <= 120"
    carbs = float(data.get("carbohydrates") or 0)
    assert carbs <= 10, f"комбуча без сахара 330g carbs {carbs} expected <= 10"
