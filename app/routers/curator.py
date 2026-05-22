"""Read-only curator endpoints: view assigned users' nutrition diaries."""

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_curator_or_admin
from app.db.models import CuratorUserAssignment, User
from app.db.repository import list_meals_for_user_local_date, list_user_measurements
from app.db.session import get_db
from app.schemas.auth import (
    MyNutritionTargetResponse,
    NutritionTargetResponse,
    WeightMeasurementPoint,
    WeightMeasurementsResponse,
    WebMealsDayResponse,
)
from app.schemas.curator import CuratorUserListItem, CuratorUserProfileResponse
from app.schemas.diary import DiarySnapshotResponse
from app.services.diary_snapshot import _resolve_tz, build_diary_snapshot
from app.services.nutrition_targets import get_active_nutrition_target, get_nutrition_target_for_range
from app.schemas.additives import DayNutritionTotals
from app.services.additive_totals import day_additive_totals_response, sum_additive_intakes_for_local_date
from app.services.web_meals_day import build_web_meal_day_row

router = APIRouter(prefix="/curator", tags=["curator"])


def _ensure_curator_can_access_user(db: Session, curator: User, user_id: int) -> User:
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if curator.role == "admin":
        return target

    exists = (
        db.query(CuratorUserAssignment.id)
        .filter(
            CuratorUserAssignment.curator_id == curator.id,
            CuratorUserAssignment.user_id == user_id,
        )
        .first()
    )
    if not exists:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not assigned to curator")

    return target


def _weight_history_cutoff(period: str) -> datetime | None:
    if period == "1m":
        return datetime.utcnow() - timedelta(days=30)
    if period == "3m":
        return datetime.utcnow() - timedelta(days=90)
    if period == "6m":
        return datetime.utcnow() - timedelta(days=180)
    if period == "1y":
        return datetime.utcnow() - timedelta(days=365)
    if period == "all":
        return None
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="period must be one of: 1m, 3m, 6m, 1y, all",
    )


@router.get("/users", response_model=list[CuratorUserListItem])
def list_curator_users(
    curator: User = Depends(require_curator_or_admin),
    db: Session = Depends(get_db),
):
    if curator.role == "admin":
        rows = (
            db.query(User)
            .filter(User.id != curator.id, User.role.in_(("user", "curator")))
            .order_by(User.created_at.desc())
            .all()
        )
    else:
        rows = (
            db.query(User)
            .join(CuratorUserAssignment, CuratorUserAssignment.user_id == User.id)
            .filter(CuratorUserAssignment.curator_id == curator.id)
            .order_by(User.created_at.desc())
            .all()
        )

    return [
        CuratorUserListItem(
            id=u.id,
            email=u.email,
            username=u.username,
            first_name=u.first_name,
            role=u.role,
            status=u.status,
            subscription_status=u.subscription_status,
            weight_kg=u.weight_kg,
            created_at=u.created_at,
        )
        for u in rows
    ]


@router.get("/users/{user_id}/profile", response_model=CuratorUserProfileResponse)
def get_curator_user_profile(
    user_id: int,
    curator: User = Depends(require_curator_or_admin),
    db: Session = Depends(get_db),
):
    target = _ensure_curator_can_access_user(db, curator, user_id)
    return CuratorUserProfileResponse(
        id=target.id,
        first_name=target.first_name,
        birth_date=target.birth_date,
        height_cm=target.height_cm,
        weight_kg=target.weight_kg,
        target_weight_kg=target.target_weight_kg,
        activity_level=target.activity_level,
    )


@router.get("/users/{user_id}/diary", response_model=DiarySnapshotResponse)
def get_curator_user_diary(
    user_id: int,
    curator: User = Depends(require_curator_or_admin),
    db: Session = Depends(get_db),
):
    target = _ensure_curator_can_access_user(db, curator, user_id)
    return build_diary_snapshot(db, target)


@router.get("/users/{user_id}/meals/day", response_model=WebMealsDayResponse)
def get_curator_user_meals_for_day(
    user_id: int,
    date_q: date = Query(..., alias="date"),
    curator: User = Depends(require_curator_or_admin),
    db: Session = Depends(get_db),
):
    target = _ensure_curator_can_access_user(db, curator, user_id)
    tz = _resolve_tz(target)
    meals = list_meals_for_user_local_date(db, target.id, date_q, tz)
    rows = [build_web_meal_day_row(m, target) for m in meals]
    additive_raw = sum_additive_intakes_for_local_date(db, target, date_q)
    additive_totals = DayNutritionTotals(**day_additive_totals_response(additive_raw))
    return WebMealsDayResponse(date=date_q, items=rows, additive_totals=additive_totals)


@router.get("/users/{user_id}/measurements", response_model=WeightMeasurementsResponse)
def get_curator_user_weight_measurements(
    user_id: int,
    period: str = Query("3m"),
    curator: User = Depends(require_curator_or_admin),
    db: Session = Depends(get_db),
):
    target = _ensure_curator_can_access_user(db, curator, user_id)
    cutoff = _weight_history_cutoff(period)
    rows = list_user_measurements(db, target.id, limit=1000)
    points: list[WeightMeasurementPoint] = []
    for row in reversed(rows):
        if row.weight_kg is None:
            continue
        if cutoff is not None and row.measured_at < cutoff:
            continue
        points.append(
            WeightMeasurementPoint(
                id=row.id,
                measured_at=row.measured_at,
                weight_kg=float(row.weight_kg),
                waist_cm=row.waist_cm,
                body_fat_percent=row.body_fat_percent,
                notes=row.notes,
            )
        )
    return WeightMeasurementsResponse(period=period, items=points)


@router.get("/users/{user_id}/nutrition-target", response_model=MyNutritionTargetResponse)
def get_curator_user_nutrition_target(
    user_id: int,
    date_q: date | None = Query(default=None, alias="date"),
    curator: User = Depends(require_curator_or_admin),
    db: Session = Depends(get_db),
):
    target = _ensure_curator_can_access_user(db, curator, user_id)
    if date_q is None:
        nt_row = get_active_nutrition_target(db, user_id=target.id)
    else:
        tz = _resolve_tz(target)
        start_local = datetime.combine(date_q, datetime.min.time(), tzinfo=tz)
        end_local = start_local + timedelta(days=1)
        start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
        nt_row = get_nutrition_target_for_range(
            db,
            user_id=target.id,
            range_start=start_utc,
            range_end=end_utc,
        )
    nt = NutritionTargetResponse.model_validate(nt_row, from_attributes=True) if nt_row is not None else None
    return {"nutrition_target": nt}
