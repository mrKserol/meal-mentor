"""Weight measurement workflow: history row, current user weight, active nutrition target."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import NutritionTarget, User, UserMeasurement
from app.db.repository import create_user_measurement
from app.services.nutrition_targets import create_or_update_active_nutrition_target


def record_weight_measurement(
    db: Session,
    user: User,
    *,
    weight_kg: float,
    measured_at: datetime | None = None,
    waist_cm: float | None = None,
    body_fat_percent: float | None = None,
    notes: str | None = None,
) -> tuple[UserMeasurement, NutritionTarget | None]:
    """Persist a new measurement and recalculate active nutrition targets atomically."""
    measurement = create_user_measurement(
        db,
        user.id,
        measured_at or datetime.utcnow(),
        weight_kg=weight_kg,
        waist_cm=waist_cm,
        body_fat_percent=body_fat_percent,
        notes=notes,
        commit=False,
    )
    db.flush()
    db.refresh(user)

    target = create_or_update_active_nutrition_target(db, user, force_new=True)
    db.commit()
    db.refresh(measurement)
    db.refresh(user)
    if target is not None:
        db.refresh(target)
    return measurement, target
