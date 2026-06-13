from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.use_cases.meal_analysis_v2 import meal_result_from_vision_dict_usda
from app.db.models import Base


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


def test_v2_response_ingredients_contain_trace_fields(db_session):
    vision_out = {
        "status": "success",
        "prediction": "Banana",
        "ingredients": {
            "banana": {
                "grams": 100,
                "state": "raw",
                "name_translated": "банан",
                "name_language": "ru",
            }
        },
        "confidence": 0.9,
    }
    fake_search = [
        {
            "banana": {
                "calories": 89,
                "protein_g": 1,
                "fat_g": 0,
                "carbs_g": 23,
                "match": "USDA: Bananas, raw",
                "product_nutrition_id": 123,
                "product_nutrition_match_id": 456,
                "nutrition_source": "usda_fdc",
                "nutrition_pipeline_version": "v2_usda",
                "nutrition_match_status": "matched",
                "nutrition_match_score": 0.92,
            }
        }
    ]
    svc = MagicMock()
    svc.search.return_value = fake_search
    svc.aggregate_nutrition_full.return_value = {"calories": 89, "protein_g": 1, "fat_g": 0, "carbs_g": 23}
    svc.aggregate_nutrition.return_value = {
        "calories": 89,
        "proteins": 1,
        "fats": 0,
        "carbohydrates": 23,
    }

    with patch("app.core.use_cases.meal_analysis_v2._get_nutrition_v2", return_value=svc):
        result = meal_result_from_vision_dict_usda(vision_out, db=db_session)

    assert result.status == "success"
    ing = result.ingredients["banana"]
    assert ing["product_nutrition_id"] == 123
    assert ing["product_nutrition_match_id"] == 456
    assert ing["nutrition_source"] == "usda_fdc"
    assert ing["nutrition_pipeline_version"] == "v2_usda"
    assert ing["nutrition_match_status"] == "matched"
    assert ing["nutrition_match_name"] == "USDA: Bananas, raw"
