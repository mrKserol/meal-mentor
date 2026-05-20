"""Tests for plan feature resolution and usage limits."""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, FeatureUsage, Plan, PlanFeature, User, UserFeatureOverride
from app.services.feature_access import get_feature_limit, get_user_feature_value, is_feature_enabled
from app.services.usage_limits import get_period_start, get_usage_count, increment_usage


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _seed_free_plan(db_session):
    plan = Plan(
        code="free",
        name="Free",
        price_amount=0,
        currency="RUB",
        period_days=30,
        is_active=True,
        sort_order=10,
    )
    db_session.add(plan)
    db_session.flush()
    db_session.add(
        PlanFeature(
            plan_id=plan.id,
            feature_key="food_photo_recognition_enabled",
            feature_name="Photo",
            value_type="boolean",
            value_bool=True,
        )
    )
    db_session.add(
        PlanFeature(
            plan_id=plan.id,
            feature_key="daily_photo_recognition_limit",
            feature_name="Daily photo",
            value_type="limit",
            value_int=3,
        )
    )
    db_session.commit()
    return plan


def test_free_plan_boolean_and_limit_defaults(db_session):
    plan = _seed_free_plan(db_session)
    user = User(email="t@example.com", subscription_status=plan.name, timezone="UTC")
    db_session.add(user)
    db_session.commit()

    assert is_feature_enabled(db_session, user.id, "food_photo_recognition_enabled") is True
    assert is_feature_enabled(db_session, user.id, "label_analysis_enabled", default=False) is False
    assert get_feature_limit(db_session, user.id, "daily_photo_recognition_limit") == 3
    assert get_feature_limit(db_session, user.id, "missing_limit", default=0) == 0


def test_user_override_wins_over_plan(db_session):
    plan = _seed_free_plan(db_session)
    user = User(email="o@example.com", subscription_status=plan.name, timezone="UTC")
    db_session.add(user)
    db_session.commit()

    db_session.add(
        UserFeatureOverride(
            user_id=user.id,
            feature_key="daily_photo_recognition_limit",
            value_type="limit",
            value_int=10,
        )
    )
    db_session.commit()

    assert get_feature_limit(db_session, user.id, "daily_photo_recognition_limit") == 10


def test_usage_increment_and_count(db_session):
    user = User(email="u@example.com", subscription_status="Free", timezone="Europe/Moscow")
    db_session.add(user)
    db_session.commit()

    increment_usage(db_session, user.id, "daily_ai_requests_limit", "daily", timezone=user.timezone)
    assert get_usage_count(db_session, user.id, "daily_ai_requests_limit", "daily", timezone=user.timezone) == 1

    increment_usage(db_session, user.id, "daily_ai_requests_limit", "daily", timezone=user.timezone)
    assert get_usage_count(db_session, user.id, "daily_ai_requests_limit", "daily", timezone=user.timezone) == 2


def test_get_period_start_monthly():
    now = datetime(2026, 5, 15, 12, 0, 0)
    assert get_period_start(now, "monthly") == date(2026, 5, 1)
    assert get_period_start(now, "daily") == date(2026, 5, 15)


def test_unlimited_limit_minus_one(db_session):
    plan = _seed_free_plan(db_session)
    db_session.add(
        PlanFeature(
            plan_id=plan.id,
            feature_key="daily_ai_requests_limit",
            feature_name="AI",
            value_type="limit",
            value_int=-1,
        )
    )
    user = User(email="unl@example.com", subscription_status=plan.name)
    db_session.add(user)
    db_session.commit()

    assert get_feature_limit(db_session, user.id, "daily_ai_requests_limit") == -1
