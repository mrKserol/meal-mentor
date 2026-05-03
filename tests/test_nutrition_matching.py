"""State-aware nutrition matching (requires data/nutrition.csv + data/food_aliases.json)."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_buckwheat_cooked_prefers_cooked_row(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"buckwheat": {"grams": 180, "state": "cooked"}}, include_candidates=True)
    assert len(rows) == 1
    data = list(rows[0].values())[0]
    assert data, "expected a match"
    m = (data.get("match") or "").lower()
    assert "cooked" in m or "boiled" in m
    assert "dry" not in m and "uncooked" not in m


def test_buckwheat_dry_prefers_dry_row(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"buckwheat": {"grams": 100, "state": "dry"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "dry" in m or "uncooked" in m or "unprepared" in m


def test_rice_cooked(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"rice": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "dry" not in m or "cooked" in m or "boiled" in m


def test_pasta_cooked(nutrition_svc: NutritionService) -> None:
    rows = nutrition_svc.search({"pasta": {"grams": 150, "state": "cooked"}})
    data = list(rows[0].values())[0]
    assert data
    m = (data.get("match") or "").lower()
    assert "cooked" in m or "dry" not in m or "macaroni" in m


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
    rows = nutrition_svc.search({"some weird ingredient xyz123": {"grams": 100, "state": "unknown"}})
    data = list(rows[0].values())[0]
    assert data == {} or data.get("calories", 0) == 0


def test_aggregate_full_mixed_format(nutrition_svc: NutritionService) -> None:
    full = nutrition_svc.aggregate_nutrition_full(
        {
            "chicken breast": {"grams": 120, "state": "grilled"},
            "salt": 2,
        }
    )
    assert full is not None
    assert full.get("calories", 0) > 0
