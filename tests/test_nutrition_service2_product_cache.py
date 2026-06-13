from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import USDA_MIN_MATCH_SCORE
from app.db.models import Base, ProductNutrition, ProductNutritionMatch
from app.infrastructure.nutrition.usda_nutrition_provider import NutritionService2
from app.infrastructure.usda.client import UsdaApiError
from app.infrastructure.usda.schemas import UsdaMatchResult


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


class FakeV1Service:
    is_available = True

    def search(self, ingredients_weights, search_type="fuzzy", threshold=0.6, **kwargs):
        name = next(iter(ingredients_weights))
        return [
            {
                name: {
                    "calories": 50,
                    "proteins": 5,
                    "fats": 2,
                    "carbohydrates": 6,
                    "match": "CSV: fallback item",
                    "weight": ingredients_weights[name].get("grams", 100)
                    if isinstance(ingredients_weights[name], dict)
                    else ingredients_weights[name],
                    "state": "raw",
                }
            }
        ]


def _good_usda_result(**overrides):
    base = UsdaMatchResult(
        input_name="banana",
        query="banana",
        grams=100,
        state="raw",
        selected_fdc_id=173944,
        selected_description="Bananas, raw",
        selected_data_type="SR Legacy",
        match_score=0.92,
        match_status="matched",
        nutrients_per_100g={"calories": 89, "protein_g": 1.1, "fat_g": 0.3, "carbs_g": 23},
        nutrients_scaled={"calories": 89, "protein_g": 1.1, "fat_g": 0.3, "carbs_g": 23},
        candidates=[],
        raw_food_json={"fdcId": 173944},
        food_category=None,
    )
    for key, val in overrides.items():
        setattr(base, key, val)
    return base


def test_first_call_persists_product_and_match(db_session):
    matcher = MagicMock()
    matcher.parse_ingredients.return_value = [
        MagicMock(input_name="banana", canonical_query="banana", grams=100, state="raw")
    ]
    matcher.raw_payload_for.return_value = {"grams": 100, "state": "raw", "usda_search_query": "banana"}
    matcher.aliases = MagicMock()
    matcher.match_ingredient.return_value = _good_usda_result()

    service = NutritionService2(db=db_session, matcher=matcher, fallback_v1=FakeV1Service())
    out = service.search({"banana": {"grams": 100, "state": "raw", "usda_search_query": "banana"}})

    row = out[0]["banana"]
    assert row["product_nutrition_id"]
    assert row["product_nutrition_match_id"]
    assert row["nutrition_source"] == "usda_fdc"
    assert db_session.query(ProductNutrition).count() == 1
    assert db_session.query(ProductNutritionMatch).count() == 1
    matcher.match_ingredient.assert_called_once()


def test_second_call_uses_db_cache_without_usda(db_session):
    matcher = MagicMock()
    ni = MagicMock(input_name="banana", canonical_query="banana", grams=100, state="raw")
    matcher.parse_ingredients.return_value = [ni]
    matcher.raw_payload_for.return_value = {"grams": 100, "state": "raw", "usda_search_query": "banana"}
    matcher.aliases = MagicMock()
    matcher.match_ingredient.return_value = _good_usda_result()

    service = NutritionService2(db=db_session, matcher=matcher, fallback_v1=FakeV1Service())
    service.search({"banana": {"grams": 100, "state": "raw", "usda_search_query": "banana"}})
    matcher.match_ingredient.reset_mock()

    out = service.search({"banana": {"grams": 100, "state": "raw", "usda_search_query": "banana"}})
    row = out[0]["banana"]
    assert row["calories"] == 89
    assert row["product_nutrition_id"]
    matcher.match_ingredient.assert_not_called()


def test_low_confidence_usda_falls_back_to_v1(db_session):
    matcher = MagicMock()
    matcher.parse_ingredients.return_value = [
        MagicMock(input_name="banana", canonical_query="banana", grams=100, state="raw")
    ]
    matcher.raw_payload_for.return_value = {"grams": 100, "state": "raw"}
    matcher.aliases = MagicMock()
    matcher.match_ingredient.return_value = _good_usda_result(match_score=USDA_MIN_MATCH_SCORE - 0.1)

    service = NutritionService2(db=db_session, matcher=matcher, fallback_v1=FakeV1Service())
    out = service.search({"banana": {"grams": 100, "state": "raw"}})
    row = out[0]["banana"]
    assert row["nutrition_source"] == "local_csv"
    assert row["nutrition_match_status"] == "fallback_csv"
    assert db_session.query(ProductNutritionMatch).count() == 0


def test_usda_error_falls_back_to_v1(db_session):
    matcher = MagicMock()
    matcher.parse_ingredients.return_value = [
        MagicMock(input_name="banana", canonical_query="banana", grams=100, state="raw")
    ]
    matcher.raw_payload_for.return_value = {"grams": 100, "state": "raw"}
    matcher.aliases = MagicMock()
    matcher.match_ingredient.side_effect = UsdaApiError("boom")

    service = NutritionService2(db=db_session, matcher=matcher, fallback_v1=FakeV1Service())
    out = service.search({"banana": {"grams": 100, "state": "raw"}})
    row = out[0]["banana"]
    assert row["nutrition_source"] == "local_csv"
