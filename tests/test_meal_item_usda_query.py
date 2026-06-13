"""Tests for usda_search_query and confidence on MealItem."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.schemas import MealLogRequest
from app.core.use_cases.meal_analysis import build_meal_items_with_nutrition_provider
from app.core.use_cases.meal_analysis_v2 import persist_meal_to_database_v2_usda
from app.db.models import Base, Meal, MealItem, ProductNutrition
from app.db.repository import create_meal, get_or_create_user
from app.db.session import get_db
from app.infrastructure.nutrition.usda_nutrition_provider import NutritionService2
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
        input_name="egg",
        query="egg whole cooked fried",
        grams=100,
        state="cooked",
        selected_fdc_id=173424,
        selected_description="Egg, whole, cooked, fried",
        selected_data_type="SR Legacy",
        match_score=0.92,
        match_status="matched",
        nutrients_per_100g={"calories": 196, "protein_g": 13, "fat_g": 15, "carbs_g": 1},
        nutrients_scaled={"calories": 196, "protein_g": 13, "fat_g": 15, "carbs_g": 1},
        candidates=[],
        raw_food_json={"fdcId": 173424},
        food_category=None,
    )
    for key, val in overrides.items():
        setattr(base, key, val)
    return base


def test_meal_item_usda_query_saved_v2(db_session):
    matcher = MagicMock()
    matcher.parse_ingredients.return_value = [
        MagicMock(input_name="egg", canonical_query="egg", grams=100, state="cooked")
    ]
    matcher.raw_payload_for.return_value = {
        "grams": 100,
        "state": "cooked",
        "confidence": 0.91,
        "usda_search_query": "egg whole cooked fried",
    }
    matcher.aliases = MagicMock()
    matcher.match_ingredient.return_value = _good_usda_result()

    service = NutritionService2(db=db_session, matcher=matcher, fallback_v1=FakeV1Fallback())
    items = build_meal_items_with_nutrition_provider(
        {
            "egg": {
                "grams": 100,
                "state": "cooked",
                "confidence": 0.91,
                "usda_search_query": "egg whole cooked fried",
            }
        },
        service,
    )
    assert items[0]["usda_search_query"] == "egg whole cooked fried"
    assert items[0]["confidence"] == 91

    user = get_or_create_user(db_session, telegram_id=9001, username="v2")
    create_meal(
        db_session,
        user.id,
        source_type="web",
        meal_datetime=datetime.utcnow(),
        items=items,
    )
    item = db_session.query(MealItem).first()
    assert item is not None
    assert item.usda_search_query == "egg whole cooked fried"
    assert item.confidence == 91


def test_meal_item_confidence_saved_v1_when_present():
    items = build_meal_items_with_nutrition_provider(
        {
            "rice": {
                "grams": 100,
                "state": "cooked",
                "confidence": 0.85,
            }
        },
        StubV1Nutrition(),
    )
    assert items[0]["confidence"] == 85
    assert items[0].get("usda_search_query") is None


def test_meals_api_returns_usda_query_and_confidence(client, db_session):
    user = get_or_create_user(db_session, telegram_id=5151, username="api")
    meal = create_meal(
        db_session,
        user.id,
        source_type="web",
        meal_datetime=datetime.utcnow(),
        items=[
            {
                "item_name": "egg",
                "estimated_weight_g": 100,
                "ingredient_state": "cooked",
                "confidence": 91,
                "usda_search_query": "egg whole cooked fried",
                "nutrition_match_name": "USDA: Egg, whole, cooked, fried",
                "nutrition_pipeline_version": "v2_usda",
                "nutrition_source": "usda_fdc",
                "nutrition": {"calories": 196, "protein_g": 13, "fat_g": 15, "carbs_g": 1},
            }
        ],
    )
    assert meal.id is not None

    resp = client.get("/meals/list", params={"telegram_id": 5151, "limit": 10})
    assert resp.status_code == 200
    item = resp.json()["items"][0]["items"][0]
    assert item["usda_search_query"] == "egg whole cooked fried"
    assert item["confidence"] == 91

    detail = client.get(f"/meals/{meal.id}", params={"telegram_id": 5151})
    assert detail.status_code == 200
    detail_item = detail.json()["items"][0]
    assert detail_item["usda_search_query"] == "egg whole cooked fried"
    assert detail_item["confidence"] == 91


def test_save_with_product_nutrition_id_preserves_usda_query(db_session):
    product = ProductNutrition(
        source="usda_fdc",
        source_food_id="173424",
        normalized_query="egg whole cooked fried",
        state="cooked",
        description="Egg, whole, cooked, fried",
        calories=196,
        protein_g=13,
        fat_g=15,
        carbs_g=1,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    req = MealLogRequest(
        telegram_id=8888,
        username="save",
        source_type="web",
        ingredients={
            "egg": {
                "grams": 100,
                "state": "cooked",
                "confidence": 0.91,
                "usda_search_query": "egg whole cooked fried",
                "product_nutrition_id": product.id,
                "nutrition_pipeline_version": "v2_usda",
                "nutrition_source": "product_nutrition_cache",
                "nutrition_match_name": "USDA: Egg, whole, cooked, fried",
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
    assert item.usda_search_query == "egg whole cooked fried"
    assert item.confidence == 91
    assert item.nutrition_pipeline_version == "v2_usda"
    assert item.nutrition_source == "product_nutrition_cache"
