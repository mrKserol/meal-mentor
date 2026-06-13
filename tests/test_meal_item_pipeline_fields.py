"""Tests for nutrition_pipeline_version and nutrition_source on MealItem."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import USDA_MIN_MATCH_SCORE
from app.core.use_cases.meal_analysis import build_meal_items_with_nutrition_provider
from app.core.use_cases.meal_analysis_v2 import persist_meal_to_database_v2_usda
from app.core.schemas import MealLogRequest
from app.db.models import Base, Meal, MealItem, ProductNutrition
from app.db.repository import create_meal, get_or_create_user
from app.db.session import get_db
from app.infrastructure.nutrition.usda_nutrition_provider import NutritionService2
from app.infrastructure.usda.client import UsdaApiError
from app.infrastructure.usda.schemas import UsdaMatchResult
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session, monkeypatch):
    monkeypatch.setattr("app.main.init_db", lambda: None)

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


class StubV1Nutrition:
    is_available = True
    aliases = None

    def search(self, ingredients_weights, search_type="fuzzy", **kwargs):
        name = next(iter(ingredients_weights))
        return [
            {
                name: {
                    "calories": 120,
                    "protein_g": 4,
                    "fat_g": 1,
                    "carbs_g": 20,
                    "match": "CSV: rice cooked",
                    "weight": 100,
                    "state": "cooked",
                }
            }
        ]


class FakeV1Fallback:
    is_available = True

    def search(self, ingredients_weights, search_type="fuzzy", **kwargs):
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


def test_meal_item_pipeline_fields_saved_v1():
    items = build_meal_items_with_nutrition_provider(
        {"rice": {"grams": 100, "state": "cooked"}},
        StubV1Nutrition(),
    )
    assert len(items) == 1
    assert items[0]["nutrition_pipeline_version"] == "v1_csv"
    assert items[0]["nutrition_source"] == "local_csv"


def test_meal_item_pipeline_fields_saved_v2_usda(db_session):
    matcher = MagicMock()
    matcher.parse_ingredients.return_value = [
        MagicMock(input_name="banana", canonical_query="banana", grams=100, state="raw")
    ]
    matcher.raw_payload_for.return_value = {"grams": 100, "state": "raw", "usda_search_query": "banana"}
    matcher.aliases = MagicMock()
    matcher.match_ingredient.return_value = _good_usda_result()

    service = NutritionService2(db=db_session, matcher=matcher, fallback_v1=FakeV1Fallback())
    items = build_meal_items_with_nutrition_provider(
        {"banana": {"grams": 100, "state": "raw", "usda_search_query": "banana"}},
        service,
    )
    assert items[0]["nutrition_pipeline_version"] == "v2_usda"
    assert items[0]["nutrition_source"] == "usda_fdc"

    matcher.match_ingredient.reset_mock()
    service.search({"banana": {"grams": 100, "state": "raw", "usda_search_query": "banana"}})
    items_cached = build_meal_items_with_nutrition_provider(
        {"banana": {"grams": 100, "state": "raw", "usda_search_query": "banana"}},
        service,
    )
    assert items_cached[0]["nutrition_pipeline_version"] == "v2_usda"
    assert items_cached[0]["nutrition_source"] == "product_nutrition_cache"
    matcher.match_ingredient.assert_not_called()


def test_meal_item_pipeline_fields_saved_v2_fallback(db_session):
    matcher = MagicMock()
    matcher.parse_ingredients.return_value = [
        MagicMock(input_name="banana", canonical_query="banana", grams=100, state="raw")
    ]
    matcher.raw_payload_for.return_value = {"grams": 100, "state": "raw"}
    matcher.aliases = MagicMock()
    matcher.match_ingredient.return_value = _good_usda_result(match_score=USDA_MIN_MATCH_SCORE - 0.1)

    service = NutritionService2(db=db_session, matcher=matcher, fallback_v1=FakeV1Fallback())
    items = build_meal_items_with_nutrition_provider(
        {"banana": {"grams": 100, "state": "raw"}},
        service,
    )
    assert items[0]["nutrition_pipeline_version"] == "v2_usda"
    assert items[0]["nutrition_source"] == "local_csv_fallback"

    matcher.match_ingredient.side_effect = UsdaApiError("boom")
    items_err = build_meal_items_with_nutrition_provider(
        {"banana": {"grams": 100, "state": "raw"}},
        service,
    )
    assert items_err[0]["nutrition_pipeline_version"] == "v2_usda"
    assert items_err[0]["nutrition_source"] == "local_csv_fallback"


def test_meals_api_returns_pipeline_fields(client, db_session):
    user = get_or_create_user(db_session, telegram_id=4242, username="tester")
    meal = create_meal(
        db_session,
        user.id,
        source_type="web",
        meal_datetime=datetime.utcnow(),
        items=[
            {
                "item_name": "rice",
                "estimated_weight_g": 150,
                "nutrition_match_name": "CSV: rice cooked",
                "nutrition_pipeline_version": "v1_csv",
                "nutrition_source": "local_csv",
                "nutrition": {"calories": 180, "protein_g": 4, "fat_g": 1, "carbs_g": 30},
            }
        ],
    )
    assert meal.id is not None

    resp = client.get("/meals/list", params={"telegram_id": 4242, "limit": 10})
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"]
    item = body["items"][0]["items"][0]
    assert item["nutrition_match_name"] == "CSV: rice cooked"
    assert item["nutrition_pipeline_version"] == "v1_csv"
    assert item["nutrition_source"] == "local_csv"

    detail = client.get(f"/meals/{meal.id}", params={"telegram_id": 4242})
    assert detail.status_code == 200
    detail_item = detail.json()["items"][0]
    assert detail_item["nutrition_pipeline_version"] == "v1_csv"
    assert detail_item["nutrition_source"] == "local_csv"


def test_v2_save_preserves_pipeline_fields_from_payload(db_session):
    product = ProductNutrition(
        source="usda_fdc",
        source_food_id="173944",
        normalized_query="banana",
        state="raw",
        description="Bananas, raw",
        calories=89,
        protein_g=1,
        fat_g=0,
        carbs_g=23,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    req = MealLogRequest(
        telegram_id=777,
        username="u",
        source_type="web",
        ingredients={
            "banana": {
                "grams": 100,
                "state": "raw",
                "product_nutrition_id": product.id,
                "nutrition_pipeline_version": "v2_usda",
                "nutrition_source": "product_nutrition_cache",
                "nutrition_match_name": "USDA: Bananas, raw",
            }
        },
    )
    with patch(
        "app.core.use_cases.meal_analysis_v2.resolve_meal_photo_urls_for_save",
        return_value=(None, None),
    ):
        resp = persist_meal_to_database_v2_usda(db_session, req)
    assert resp.status == "success"

    item = db_session.query(MealItem).join(Meal).filter(Meal.user_id.isnot(None)).first()
    assert item is not None
    assert item.nutrition_pipeline_version == "v2_usda"
    assert item.nutrition_source == "product_nutrition_cache"
