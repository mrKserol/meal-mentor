"""Tests for automatic goal derivation from weight vs target."""

from app.services.user_goal import (
    GOAL_GAIN_WEIGHT,
    GOAL_LOSE_WEIGHT,
    GOAL_MAINTAIN_WEIGHT,
    derive_goal_from_weights,
    sync_user_goal,
)
from app.db.models import User


def test_derive_lose_weight():
    assert derive_goal_from_weights(80.0, 70.0) == GOAL_LOSE_WEIGHT


def test_derive_gain_weight():
    assert derive_goal_from_weights(60.0, 70.0) == GOAL_GAIN_WEIGHT


def test_derive_maintain_weight():
    assert derive_goal_from_weights(70.0, 70.0) == GOAL_MAINTAIN_WEIGHT


def test_derive_none_when_incomplete():
    assert derive_goal_from_weights(None, 70.0) is None
    assert derive_goal_from_weights(70.0, None) is None


def test_sync_user_goal_sets_user_field():
    user = User(weight_kg=75.0, target_weight_kg=70.0)
    assert sync_user_goal(user) == GOAL_LOSE_WEIGHT
    assert user.goal == GOAL_LOSE_WEIGHT
