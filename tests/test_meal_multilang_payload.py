"""Multilingual meal payload parsing and item specs."""

from __future__ import annotations

from app.core.use_cases.meal_analysis import (
    _build_meal_items,
    _meal_result_from_vision_dict,
    enrich_meal_display_fields,
)
from app.infrastructure.ai.openai_food_client import _normalize_model_json


def test_normalize_model_json_keeps_translated_fields() -> None:
    raw = {
        "prediction": "Pasta with beef",
        "prediction_translated": "Паста с говядиной",
        "prediction_language": "ru",
        "ingredients": {
            "ground beef": {
                "grams": 100,
                "state": "fried",
                "name_translated": "говяжий фарш",
                "name_language": "ru",
            }
        },
        "confidence": 0.8,
    }
    ingredients, conf = _normalize_model_json(raw)
    assert conf == 0.8
    assert ingredients["ground beef"]["grams"] == 100
    assert ingredients["ground beef"]["state"] == "fried"
    assert ingredients["ground beef"]["name_translated"] == "говяжий фарш"
    assert ingredients["ground beef"]["name_language"] == "ru"


def test_meal_result_from_vision_dict_translated_prediction() -> None:
    out = {
        "status": "success",
        "ingredients": {"rice": {"grams": 100, "state": "cooked"}},
        "confidence": 0.9,
        "prediction": "Rice bowl",
        "prediction_translated": "Рис",
        "prediction_language": "RU",
    }
    result = _meal_result_from_vision_dict(out)
    assert result.status == "success"
    assert result.prediction == "Rice bowl"
    assert result.prediction_translated == "Рис"
    assert result.prediction_language == "ru"


def test_build_meal_items_legacy_numeric() -> None:
    class _StubNutrition:
        is_available = False
        aliases = None

        def search(self, *args, **kwargs):
            return []

    items = _build_meal_items({"rice": 100}, _StubNutrition())  # type: ignore[arg-type]
    assert len(items) == 1
    assert items[0]["item_name"] == "rice"
    assert items[0].get("name_translated") is None


def test_enrich_meal_display_fields_legacy_text_shape() -> None:
    result = enrich_meal_display_fields(
        _meal_result_from_vision_dict(
            {
                "status": "success",
                "ingredients": {
                    "buckwheat": {"grams": 180, "state": "cooked"},
                    "chicken breast": {"grams": 120, "state": "fried"},
                },
                "confidence": 0.76,
                "prediction": "Гречка с курицей",
                "prediction_translated": None,
                "prediction_language": None,
            }
        ),
        user_language="ru",
    )
    assert result.prediction_translated == "Гречка с курицей"
    assert result.ingredients["buckwheat"]["name_translated"] == "гречка"


def test_build_meal_items_with_name_translated() -> None:
    class _StubNutrition:
        is_available = False
        aliases = None

        def search(self, *args, **kwargs):
            return []

    ingredients = {
        "rice": {
            "grams": 100,
            "state": "cooked",
            "name_translated": "рис",
            "name_language": "ru",
        }
    }
    items = _build_meal_items(ingredients, _StubNutrition())  # type: ignore[arg-type]
    assert items[0]["item_name"] == "rice"
    assert items[0]["name_translated"] == "рис"
    assert items[0]["name_language"] == "ru"
