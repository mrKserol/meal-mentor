"""Resolve plan features and overrides for a user."""

from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.db.models import Plan, PlanFeature, User, UserFeatureOverride
from app.db.repository import get_active_subscription


def _feature_value(row: PlanFeature | UserFeatureOverride) -> bool | int | str | None:
    if row.value_type == "boolean":
        return bool(row.value_bool)
    if row.value_type == "limit":
        return row.value_int
    if row.value_type == "text":
        return row.value_text
    return row.value_text if row.value_text is not None else row.value_int


def _resolve_plan(db: Session, user_id: int) -> Plan | None:
    active_subscription = get_active_subscription(db, user_id)
    plan: Plan | None = None

    if active_subscription and active_subscription.plan_id:
        plan = (
            db.query(Plan)
            .options(joinedload(Plan.features))
            .filter(Plan.id == active_subscription.plan_id)
            .first()
        )

    if active_subscription and plan is None and active_subscription.plan:
        plan = (
            db.query(Plan)
            .options(joinedload(Plan.features))
            .filter(Plan.code == active_subscription.plan)
            .first()
        )

    if plan is None:
        plan = db.query(Plan).options(joinedload(Plan.features)).filter(Plan.code == "free").first()

    return plan


def get_user_feature_value(db: Session, user_id: int, feature_key: str) -> bool | int | str | None:
    """
    Итоговое значение feature:
    - сначала user override;
    - затем feature активного тарифа;
    - иначе None (вызывающий код применяет default).
    """
    override = (
        db.query(UserFeatureOverride)
        .filter(
            UserFeatureOverride.user_id == user_id,
            UserFeatureOverride.feature_key == feature_key,
        )
        .first()
    )
    if override is not None:
        return _feature_value(override)

    plan = _resolve_plan(db, user_id)
    if plan is not None:
        for feature in plan.features:
            if feature.feature_key == feature_key:
                return _feature_value(feature)

    return None


def is_feature_enabled(db: Session, user_id: int, feature_key: str, default: bool = False) -> bool:
    value = get_user_feature_value(db, user_id, feature_key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def get_feature_limit(db: Session, user_id: int, feature_key: str, default: int = 0) -> int:
    value = get_user_feature_value(db, user_id, feature_key)
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def build_features_map(db: Session, user: User) -> dict[str, Any]:
    """Совместимость с build_user_entitlements: словарь feature_key -> значение."""
    plan = _resolve_plan(db, user.id)
    features: dict[str, bool | int | str | None] = {}
    if plan is not None:
        for feature in plan.features:
            features[feature.feature_key] = _feature_value(feature)

    overrides = db.query(UserFeatureOverride).filter(UserFeatureOverride.user_id == user.id).all()
    for override in overrides:
        features[override.feature_key] = _feature_value(override)

    return features
