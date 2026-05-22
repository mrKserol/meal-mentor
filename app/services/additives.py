"""User supplement additives and intake history (separate from meals)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import zoneinfo
from sqlalchemy.orm import Session

from app.db.models import Additive, AdditiveIntake, User
from app.db.nutrition_columns import INTEGER_NUTRITION_KEYS, MEAL_ITEM_NUTRITION_KEYS
from app.services.user_timezone import meal_datetime_for_local_date_end, resolve_tz


def nutrient_payload_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in MEAL_ITEM_NUTRITION_KEYS:
        if key not in data:
            continue
        val = data[key]
        if val is None or val == "":
            continue
        try:
            if key in INTEGER_NUTRITION_KEYS:
                out[key] = int(round(float(val)))
            else:
                out[key] = float(val)
        except (TypeError, ValueError):
            continue
    return out


def list_user_additives(db: Session, user_id: int) -> list[Additive]:
    return (
        db.query(Additive)
        .filter(Additive.user_id == user_id, Additive.deleted_at.is_(None))
        .order_by(Additive.created_at.desc())
        .all()
    )


def get_user_additive(db: Session, user_id: int, additive_id: int) -> Additive | None:
    return (
        db.query(Additive)
        .filter(
            Additive.id == additive_id,
            Additive.user_id == user_id,
            Additive.deleted_at.is_(None),
        )
        .first()
    )


def create_user_additive(
    db: Session,
    user_id: int,
    additive_name: str,
    serving_label: str | None,
    serving_size_g: float | None,
    nutrients: dict[str, Any],
    photo_large: str | None = None,
    photo_thumb: str | None = None,
) -> Additive:
    payload = nutrient_payload_from_dict(nutrients)
    row = Additive(
        user_id=user_id,
        additive_name=additive_name.strip(),
        serving_label=serving_label,
        serving_size_g=serving_size_g,
        photo_large=photo_large,
        photo_thumb=photo_thumb,
    )
    for key, val in payload.items():
        setattr(row, key, val)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_user_additive(
    db: Session,
    user_id: int,
    additive_id: int,
    payload: dict[str, Any],
) -> Additive | None:
    row = get_user_additive(db, user_id, additive_id)
    if row is None:
        return None

    if "additive_name" in payload and payload["additive_name"] is not None:
        row.additive_name = str(payload["additive_name"]).strip()
    if "serving_label" in payload:
        row.serving_label = payload["serving_label"]
    if "serving_size_g" in payload:
        row.serving_size_g = payload["serving_size_g"]
    if "photo_large" in payload and payload["photo_large"] is not None:
        row.photo_large = payload["photo_large"]
    if "photo_thumb" in payload and payload["photo_thumb"] is not None:
        row.photo_thumb = payload["photo_thumb"]

    if "nutrients" in payload and payload["nutrients"] is not None:
        for key in MEAL_ITEM_NUTRITION_KEYS:
            setattr(row, key, None)
        nut_payload = nutrient_payload_from_dict(payload["nutrients"])
        for key, val in nut_payload.items():
            setattr(row, key, val)

    db.commit()
    db.refresh(row)
    return row


def soft_delete_user_additive(db: Session, user_id: int, additive_id: int) -> bool:
    row = get_user_additive(db, user_id, additive_id)
    if row is None:
        return False
    row.deleted_at = datetime.utcnow()
    db.commit()
    return True


def _local_day_range_utc(user: User, d: date) -> tuple[datetime, datetime]:
    tz = resolve_tz(user)
    start_local = datetime.combine(d, datetime.min.time(), tzinfo=tz)
    end_local = datetime.combine(d + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def list_user_additive_intakes_for_local_date(db: Session, user: User, d: date) -> list[AdditiveIntake]:
    start_utc, end_utc = _local_day_range_utc(user, d)
    return (
        db.query(AdditiveIntake)
        .filter(
            AdditiveIntake.user_id == user.id,
            AdditiveIntake.intake_datetime >= start_utc,
            AdditiveIntake.intake_datetime < end_utc,
        )
        .order_by(AdditiveIntake.intake_datetime.desc())
        .all()
    )


def _scaled_nutrients_from_additive(additive: Additive, servings_count: float) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in MEAL_ITEM_NUTRITION_KEYS:
        val = getattr(additive, key, None)
        if val is None:
            continue
        scaled = float(val) * servings_count
        if key in INTEGER_NUTRITION_KEYS:
            payload[key] = int(round(scaled))
        else:
            payload[key] = scaled
    return payload


def record_additive_intake(
    db: Session,
    user: User,
    additive_id: int,
    servings_count: float,
    intake_local_date: date | None = None,
) -> AdditiveIntake:
    if servings_count <= 0:
        raise ValueError("servings_count must be positive")

    additive = get_user_additive(db, user.id, additive_id)
    if additive is None:
        raise ValueError("additive not found")

    if intake_local_date is not None:
        intake_dt = meal_datetime_for_local_date_end(user, intake_local_date)
    else:
        intake_dt = datetime.utcnow()

    row = AdditiveIntake(
        user_id=user.id,
        additive_id=additive.id,
        additive_name_snapshot=additive.additive_name,
        servings_count=servings_count,
        intake_datetime=intake_dt,
    )
    for key, val in _scaled_nutrients_from_additive(additive, servings_count).items():
        setattr(row, key, val)

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def record_water_intake(
    db: Session,
    user: User,
    amount_ml: float = 100,
    intake_local_date: date | None = None,
) -> AdditiveIntake:
    if amount_ml <= 0:
        raise ValueError("amount_ml must be positive")

    if intake_local_date is not None:
        intake_dt = meal_datetime_for_local_date_end(user, intake_local_date)
    else:
        intake_dt = datetime.utcnow()

    row = AdditiveIntake(
        user_id=user.id,
        additive_id=None,
        additive_name_snapshot="Water",
        servings_count=1.0,
        intake_datetime=intake_dt,
        water_g=amount_ml,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_user_additive_intake(db: Session, user_id: int, intake_id: int) -> bool:
    row = (
        db.query(AdditiveIntake)
        .filter(AdditiveIntake.id == intake_id, AdditiveIntake.user_id == user_id)
        .first()
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
