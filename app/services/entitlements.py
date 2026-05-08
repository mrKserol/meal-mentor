from datetime import datetime
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


def build_user_entitlements(db: Session, user: User) -> dict[str, Any]:
    active_subscription = get_active_subscription(db, user.id)
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

    features: dict[str, bool | int | str | None] = {}
    if plan is not None:
        for feature in plan.features:
            features[feature.feature_key] = _feature_value(feature)

    overrides = db.query(UserFeatureOverride).filter(UserFeatureOverride.user_id == user.id).all()
    for override in overrides:
        features[override.feature_key] = _feature_value(override)

    ends_at: datetime | None = active_subscription.ends_at if active_subscription else None
    return {
        "plan": {
            "code": plan.code if plan else "free",
            "name": plan.name if plan else "Бесплатный",
            "ends_at": ends_at.isoformat() if ends_at else None,
        },
        "features": features,
    }
