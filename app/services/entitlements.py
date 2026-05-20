from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import User
from app.db.repository import get_active_subscription
from app.services.feature_access import _resolve_plan, build_features_map


def build_user_entitlements(db: Session, user: User) -> dict[str, Any]:
    active_subscription = get_active_subscription(db, user.id)
    plan = _resolve_plan(db, user.id)
    features = build_features_map(db, user)
    ends_at: datetime | None = active_subscription.ends_at if active_subscription else None
    return {
        "plan": {
            "code": plan.code if plan else "free",
            "name": plan.name if plan else "Бесплатный",
            "ends_at": ends_at.isoformat() if ends_at else None,
        },
        "features": features,
    }
