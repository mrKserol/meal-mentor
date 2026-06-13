from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.use_cases.nutrition_pipeline_selector import (
    get_global_nutrition_pipeline,
    normalize_global_pipeline_version,
    normalize_user_pipeline_version,
    resolve_user_nutrition_pipeline,
    set_global_nutrition_pipeline,
)
from app.db.models import Base, User


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_invalid_user_value_normalizes_to_global():
    assert normalize_user_pipeline_version("bad") == "global"
    assert normalize_user_pipeline_version(None) == "global"


def test_invalid_global_value_normalizes_to_v1_csv():
    assert normalize_global_pipeline_version("bad") == "v1_csv"
    assert normalize_global_pipeline_version(None) == "v1_csv"


def test_user_v1_csv_overrides_global_v2_usda():
    db = _session()
    try:
        set_global_nutrition_pipeline(db, "v2_usda")
        user = User(email="u1@example.test", nutrition_pipeline_version="v1_csv")
        db.add(user)
        db.commit()
        assert resolve_user_nutrition_pipeline(db, user) == "v1_csv"
    finally:
        db.close()


def test_user_v2_usda_overrides_global_v1_csv():
    db = _session()
    try:
        set_global_nutrition_pipeline(db, "v1_csv")
        user = User(email="u2@example.test", nutrition_pipeline_version="v2_usda")
        db.add(user)
        db.commit()
        assert resolve_user_nutrition_pipeline(db, user) == "v2_usda"
    finally:
        db.close()


def test_user_global_uses_global_setting():
    db = _session()
    try:
        assert get_global_nutrition_pipeline(db) == "v1_csv"
        set_global_nutrition_pipeline(db, "v2_usda")
        user = User(email="u3@example.test", nutrition_pipeline_version="global")
        db.add(user)
        db.commit()
        assert resolve_user_nutrition_pipeline(db, user) == "v2_usda"
    finally:
        db.close()
