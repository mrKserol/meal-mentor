"""Tests for atomic feature usage increments."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, FeatureUsage, User
from app.services.usage_limits import (
    get_usage_count,
    increment_many_usage,
    increment_usage,
    record_photo_recognition_usage,
)


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


def _make_user(db_session) -> User:
    user = User(email="usage@test.com", subscription_status="Free", timezone="UTC")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_increment_usage_with_commit_increases_counter(db_session):
    user = _make_user(db_session)

    increment_usage(db_session, user.id, "daily_ai_requests_limit", "daily", timezone=user.timezone)

    assert get_usage_count(db_session, user.id, "daily_ai_requests_limit", "daily", timezone=user.timezone) == 1


def test_increment_many_usage_creates_multiple_counters(db_session):
    user = _make_user(db_session)

    increment_many_usage(
        db_session,
        user.id,
        [
            ("daily_photo_recognition_limit", "daily"),
            ("monthly_photo_recognition_limit", "monthly"),
            ("daily_ai_requests_limit", "daily"),
        ],
        timezone=user.timezone,
    )

    assert get_usage_count(db_session, user.id, "daily_photo_recognition_limit", "daily", timezone=user.timezone) == 1
    assert get_usage_count(db_session, user.id, "monthly_photo_recognition_limit", "monthly", timezone=user.timezone) == 1
    assert get_usage_count(db_session, user.id, "daily_ai_requests_limit", "daily", timezone=user.timezone) == 1


def test_record_photo_recognition_usage_increments_all_related_counters(db_session):
    user = _make_user(db_session)

    record_photo_recognition_usage(db_session, user)

    assert get_usage_count(db_session, user.id, "daily_photo_recognition_limit", "daily", timezone=user.timezone) == 1
    assert get_usage_count(db_session, user.id, "monthly_photo_recognition_limit", "monthly", timezone=user.timezone) == 1
    assert get_usage_count(db_session, user.id, "daily_ai_requests_limit", "daily", timezone=user.timezone) == 1


def test_record_photo_recognition_usage_second_call_increments_to_two(db_session):
    user = _make_user(db_session)

    record_photo_recognition_usage(db_session, user)
    record_photo_recognition_usage(db_session, user)

    assert get_usage_count(db_session, user.id, "daily_photo_recognition_limit", "daily", timezone=user.timezone) == 2
    assert get_usage_count(db_session, user.id, "monthly_photo_recognition_limit", "monthly", timezone=user.timezone) == 2
    assert get_usage_count(db_session, user.id, "daily_ai_requests_limit", "daily", timezone=user.timezone) == 2


def test_increment_many_usage_rolls_back_on_failure(db_session, monkeypatch):
    user = _make_user(db_session)
    calls: list[str] = []

    original_increment = increment_usage

    def flaky_increment(*args, **kwargs):
        calls.append(kwargs.get("feature_key", ""))
        if len(calls) == 2:
            raise RuntimeError("simulated failure")
        return original_increment(*args, **kwargs)

    monkeypatch.setattr("app.services.usage_limits.increment_usage", flaky_increment)

    with pytest.raises(RuntimeError, match="simulated failure"):
        increment_many_usage(
            db_session,
            user.id,
            [
                ("daily_photo_recognition_limit", "daily"),
                ("monthly_photo_recognition_limit", "monthly"),
                ("daily_ai_requests_limit", "daily"),
            ],
            timezone=user.timezone,
        )

    assert (
        db_session.query(FeatureUsage)
        .filter(FeatureUsage.user_id == user.id)
        .count()
        == 0
    )
