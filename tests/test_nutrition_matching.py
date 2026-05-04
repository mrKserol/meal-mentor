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


def test_milk_tea_debug_log(caplog: pytest.LogCaptureFixture, nutrition_svc: NutritionService) -> None:
    caplog.set_level(logging.INFO)
    nutrition_svc.search({"milk tea": {"grams": 200, "state": "unknown"}})
    assert any("nutrition_milk_tea_debug" in r.message for r in caplog.records)


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
