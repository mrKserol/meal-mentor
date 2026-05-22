"""Aggregate additive intake nutrients for diary totals."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import AdditiveIntake, User
from app.db.nutrition_columns import INTEGER_NUTRITION_KEYS, MEAL_ITEM_NUTRITION_KEYS
from app.services.user_timezone import resolve_tz

_PRIMARY_DAY_TOTAL_KEYS = (
    "calories",
    "protein_g",
    "fat_g",
    "carbs_g",
    "fiber_g",
    "sugar_g",
    "sodium_mg",
    "saturated_fat_g",
    "water_g",
)


def _empty_totals() -> dict[str, float]:
    return {k: 0.0 for k in _PRIMARY_DAY_TOTAL_KEYS}


def _sum_intake_rows(rows: list[AdditiveIntake]) -> dict[str, float]:
    totals = _empty_totals()
    for row in rows:
        for key in MEAL_ITEM_NUTRITION_KEYS:
            if key not in totals:
                continue
            val = getattr(row, key, None)
            if val is not None:
                totals[key] = totals.get(key, 0.0) + float(val)
    if "calories" in totals:
        totals["calories"] = float(int(round(totals["calories"])))
    return totals


def sum_additive_intakes_for_range(
    db: Session,
    user_id: int,
    start_utc: datetime,
    end_utc: datetime,
) -> dict[str, float]:
    rows = (
        db.query(AdditiveIntake)
        .filter(
            AdditiveIntake.user_id == user_id,
            AdditiveIntake.intake_datetime >= start_utc,
            AdditiveIntake.intake_datetime < end_utc,
        )
        .all()
    )
    return _sum_intake_rows(rows)


def sum_additive_intakes_for_local_date(db: Session, user: User, d: date) -> dict[str, float]:
    tz = resolve_tz(user)
    start_local = datetime.combine(d, datetime.min.time(), tzinfo=tz)
    end_local = datetime.combine(d + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return sum_additive_intakes_for_range(db, user.id, start_utc, end_utc)


def _init_detailed_sums() -> dict[str, float]:
    _primary = frozenset({"calories", "protein_g", "fat_g", "carbs_g", "fiber_g"})
    return {k: 0.0 for k in MEAL_ITEM_NUTRITION_KEYS if k not in _primary}


def accumulate_additive_intakes_detailed(rows: list[AdditiveIntake], totals: dict[str, float]) -> None:
    for row in rows:
        for key in totals.keys():
            totals[key] += float(getattr(row, key, 0.0) or 0.0)


def list_additive_intakes_for_range(
    db: Session,
    user_id: int,
    start_utc: datetime,
    end_utc: datetime,
) -> list[AdditiveIntake]:
    return (
        db.query(AdditiveIntake)
        .filter(
            AdditiveIntake.user_id == user_id,
            AdditiveIntake.intake_datetime >= start_utc,
            AdditiveIntake.intake_datetime < end_utc,
        )
        .all()
    )


def primary_macros_from_intakes(rows: list[AdditiveIntake]) -> dict[str, float]:
    out = {"calories": 0.0, "protein_g": 0.0, "fat_g": 0.0, "carbs_g": 0.0, "fiber_g": 0.0}
    for row in rows:
        out["calories"] += float(row.calories or 0)
        out["protein_g"] += float(row.protein_g or 0)
        out["fat_g"] += float(row.fat_g or 0)
        out["carbs_g"] += float(row.carbs_g or 0)
        out["fiber_g"] += float(row.fiber_g or 0)
    return out


def day_additive_totals_response(totals: dict[str, float]) -> dict[str, float]:
    """Shape for WebMealsDayResponse.additive_totals."""
    out = _empty_totals()
    for key in _PRIMARY_DAY_TOTAL_KEYS:
        out[key] = float(totals.get(key, 0.0) or 0.0)
    out["calories"] = float(int(round(out["calories"])))
    return out
