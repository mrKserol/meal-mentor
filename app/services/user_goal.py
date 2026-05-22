"""Derive user.goal from current vs target weight."""

from __future__ import annotations

from app.db.models import User

GOAL_LOSE_WEIGHT = "lose_weight"
GOAL_GAIN_WEIGHT = "gain_weight"
GOAL_MAINTAIN_WEIGHT = "maintain_weight"


def derive_goal_from_weights(
    weight_kg: float | None,
    target_weight_kg: float | None,
) -> str | None:
    if weight_kg is None or target_weight_kg is None:
        return None
    current = float(weight_kg)
    target = float(target_weight_kg)
    if current > target:
        return GOAL_LOSE_WEIGHT
    if current < target:
        return GOAL_GAIN_WEIGHT
    return GOAL_MAINTAIN_WEIGHT


def sync_user_goal(user: User) -> str | None:
    """Set user.goal from weight_kg and target_weight_kg. Returns the new goal."""
    goal = derive_goal_from_weights(user.weight_kg, user.target_weight_kg)
    user.goal = goal
    return goal
