from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, ProductNutrition, ProductNutritionMatch
from app.infrastructure.nutrition.product_nutrition_repository import (
    get_product_match,
    normalize_product_query,
    scale_product_nutrition,
    upsert_product_match,
    upsert_product_nutrition,
)


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_upsert_product_nutrition_creates_product():
    db = _session()
    try:
        product = upsert_product_nutrition(
            db,
            source="usda_fdc",
            source_food_id="173944",
            normalized_query="banana",
            state="raw",
            description="Bananas, raw",
            data_type="SR Legacy",
            food_category=None,
            match_score=0.92,
            match_status="matched",
            nutrients_per_100g={"calories": 89, "protein_g": 1.1, "fat_g": 0.3, "carbs_g": 23},
            raw_source={"fdcId": 173944},
        )
        db.commit()
        assert product.id is not None
        assert product.calories == 89
        assert product.protein_g == 1
    finally:
        db.close()


def test_upsert_product_nutrition_updates_by_source_food_id():
    db = _session()
    try:
        first = upsert_product_nutrition(
            db,
            source="usda_fdc",
            source_food_id="173944",
            normalized_query="banana",
            state="raw",
            description="Bananas, raw",
            data_type="SR Legacy",
            food_category=None,
            match_score=0.92,
            match_status="matched",
            nutrients_per_100g={"calories": 89, "protein_g": 1.1},
            raw_source={"fdcId": 173944},
        )
        db.commit()
        second = upsert_product_nutrition(
            db,
            source="usda_fdc",
            source_food_id="173944",
            normalized_query="banana",
            state="raw",
            description="Bananas, raw, updated",
            data_type="SR Legacy",
            food_category=None,
            match_score=0.95,
            match_status="matched",
            nutrients_per_100g={"calories": 90, "protein_g": 1.2},
            raw_source={"fdcId": 173944, "updated": True},
        )
        db.commit()
        count = db.query(ProductNutrition).count()
        assert count == 1
        assert second.id == first.id
        assert second.description == "Bananas, raw, updated"
        assert second.calories == 90
    finally:
        db.close()


def test_upsert_product_match_creates_and_updates():
    db = _session()
    try:
        product = upsert_product_nutrition(
            db,
            source="usda_fdc",
            source_food_id="999",
            normalized_query="buckwheat",
            state="cooked",
            description="Buckwheat groats, cooked",
            data_type="SR Legacy",
            food_category=None,
            match_score=0.9,
            match_status="matched",
            nutrients_per_100g={"calories": 92, "protein_g": 3.4},
            raw_source={"fdcId": 999},
        )
        db.commit()
        match = upsert_product_match(
            db,
            normalized_query="buckwheat",
            state="cooked",
            source="usda_fdc",
            product_nutrition_id=product.id,
            match_score=0.9,
            match_status="matched",
            selected_description="Buckwheat groats, cooked",
            selected_source_food_id="999",
            selected_data_type="SR Legacy",
        )
        db.commit()
        assert match.id is not None
        found = get_product_match(db, normalized_query="buckwheat", state="cooked", source="usda_fdc")
        assert found is not None
        assert found.product_nutrition_id == product.id

        updated = upsert_product_match(
            db,
            normalized_query="buckwheat",
            state="cooked",
            source="usda_fdc",
            product_nutrition_id=product.id,
            match_score=0.95,
            match_status="matched",
            selected_description="Buckwheat groats, cooked, roasted",
            selected_source_food_id="999",
            selected_data_type="SR Legacy",
        )
        db.commit()
        assert db.query(ProductNutritionMatch).count() == 1
        assert updated.match_score == 0.95
        assert updated.selected_description == "Buckwheat groats, cooked, roasted"
    finally:
        db.close()


def test_scale_product_nutrition_scales_to_grams():
    db = _session()
    try:
        product = upsert_product_nutrition(
            db,
            source="usda_fdc",
            source_food_id="173944",
            normalized_query="banana",
            state="raw",
            description="Bananas, raw",
            data_type="SR Legacy",
            food_category=None,
            match_score=0.92,
            match_status="matched",
            nutrients_per_100g={"calories": 100, "protein_g": 10, "fiber_g": 2.5},
            raw_source={"fdcId": 173944},
        )
        scaled = scale_product_nutrition(product, 200)
        assert scaled["calories"] == 200
        assert scaled["protein_g"] == 20
        assert scaled["fiber_g"] == 5.0
    finally:
        db.close()


def test_normalize_product_query():
    assert normalize_product_query("  Boiled   Buckwheat ") == "boiled buckwheat"
