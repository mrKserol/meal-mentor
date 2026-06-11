from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import AdditiveIntake, Allergen, Base, Meal, MealItem, MealItemNutrition, NutritionTarget, User, UserMeasurement
from app.services.ai_chat_context import build_ai_chat_context


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


def _user(db_session, **kwargs) -> User:
    user = User(email=kwargs.pop("email", "ai-context@test.com"), timezone="UTC", language="ru", **kwargs)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_ai_chat_context_empty_diary(db_session):
    user = _user(db_session)

    context = build_ai_chat_context(db_session, user)

    assert context["user_profile"]["language"] == "ru"
    assert context["nutrition_14d"]["days_with_food_logs"] == 0
    assert context["nutrition_14d"]["daily_summary"] == []
    assert context["nutrition_14d"]["recent_meals"] == []
    assert context["data_quality"]["has_targets"] is False


def test_ai_chat_context_collects_14d_data(db_session):
    user = _user(
        db_session,
        sex="male",
        birth_date=date(1990, 1, 1),
        height_cm=180,
        weight_kg=82,
        target_weight_kg=78,
        goal="lose_weight",
        activity_level="moderate",
    )
    db_session.add(Allergen(user_id=user.id, allergen_key="peanuts"))
    db_session.add(
        NutritionTarget(
            user_id=user.id,
            bmr_kcal=1700,
            tdee_kcal=2400,
            target_calories=2100,
            target_fiber_g=25,
            target_protein_g=140,
            target_fat_g=70,
            target_carbs_g=220,
            is_active=True,
        )
    )
    meal = Meal(
        user_id=user.id,
        meal_datetime=datetime.utcnow() - timedelta(days=1),
        prediction_translated="Йогурт с бананом",
        user_text="йогурт с бананом",
    )
    item = MealItem(item_name="yogurt", name_translated="йогурт", estimated_weight_g=200)
    item.nutrition = MealItemNutrition(
        calories=300,
        protein_g=18,
        fat_g=7,
        carbs_g=42,
        fiber_g=6,
        sugar_g=18,
        sodium_mg=150,
        saturated_fat_g=3,
        water_g=120,
    )
    meal.items.append(item)
    db_session.add(meal)
    db_session.add(
        AdditiveIntake(
            user_id=user.id,
            additive_name_snapshot="Water",
            servings_count=1,
            intake_datetime=datetime.utcnow() - timedelta(days=1),
            water_g=300,
        )
    )
    db_session.add(UserMeasurement(user_id=user.id, measured_at=datetime.utcnow() - timedelta(days=10), weight_kg=83))
    db_session.add(UserMeasurement(user_id=user.id, measured_at=datetime.utcnow() - timedelta(days=1), weight_kg=82))
    db_session.commit()

    context = build_ai_chat_context(db_session, user)

    assert context["user_profile"]["allergens"] == ["peanuts"]
    assert context["nutrition_targets"]["calories_kcal"] == 2100
    assert context["nutrition_14d"]["days_with_food_logs"] == 1
    assert context["nutrition_14d"]["daily_summary"][0]["calories_kcal"] == 300
    assert context["nutrition_14d"]["recent_meals"][0]["meal_name"] == "Йогурт с бананом"
    assert context["weight"]["trend_14d_kg"] == -1.0
    assert context["water"]["avg_daily_water_ml_14d"] == 420
    assert context["data_quality"]["days_with_supplement_logs"] == 1
