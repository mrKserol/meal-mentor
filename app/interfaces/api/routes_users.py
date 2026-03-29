from datetime import date, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repository import (
    create_user_measurement,
    delete_last_weight_measurement,
    get_or_create_user,
    get_user_by_telegram_id,
    list_user_measurements,
)
from app.core.use_cases.profile_completeness import is_profile_complete, missing_profile_fields

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    sex: str | None = None
    birth_date: date | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    target_weight_kg: float | None = None
    goal: str | None = None
    activity_level: str | None = None
    timezone: str | None = None


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    sex: str | None
    birth_date: date | None
    height_cm: int | None
    weight_kg: float | None
    target_weight_kg: float | None
    goal: str | None
    activity_level: str | None
    timezone: str | None

    class Config:
        from_attributes = True


class ProfilePatch(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    sex: str | None = None
    birth_date: date | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    target_weight_kg: float | None = None
    goal: str | None = None
    activity_level: str | None = None
    timezone: str | None = None


class WeightBody(BaseModel):
    telegram_id: int
    weight_kg: float


def _user_to_dict(user) -> dict[str, Any]:
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "sex": user.sex,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "target_weight_kg": user.target_weight_kg,
        "goal": user.goal,
        "activity_level": user.activity_level,
        "timezone": user.timezone,
    }


@router.post("/register", response_model=UserResponse)
def register_user(data: UserCreate, db: Session = Depends(get_db)):
    user = get_or_create_user(
        db,
        telegram_id=data.telegram_id,
        username=data.username,
        first_name=data.first_name,
        sex=data.sex,
        birth_date=data.birth_date,
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        target_weight_kg=data.target_weight_kg,
        goal=data.goal,
        activity_level=data.activity_level,
        timezone=data.timezone,
    )
    return user


@router.get("/profile")
def get_profile(telegram_id: int = Query(...), db: Session = Depends(get_db)):
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {
            "user": None,
            "profile_complete": False,
            "missing_fields": list(missing_profile_fields(None)),
        }
    return {
        "user": _user_to_dict(user),
        "profile_complete": is_profile_complete(user),
        "missing_fields": missing_profile_fields(user),
    }


@router.patch("/profile")
def patch_profile(body: ProfilePatch, db: Session = Depends(get_db)):
    raw = body.model_dump(exclude_unset=True, exclude_none=True)
    tid = raw.pop("telegram_id", None)
    if tid is None:
        raise HTTPException(400, "telegram_id required")
    user = get_or_create_user(db, telegram_id=tid, **{k: v for k, v in raw.items() if v is not None})
    return {"user": _user_to_dict(user), "profile_complete": is_profile_complete(user)}


@router.post("/weights")
def add_weight(body: WeightBody, db: Session = Depends(get_db)):
    user = get_user_by_telegram_id(db, body.telegram_id)
    if not user:
        raise HTTPException(404, "user not found")
    m = create_user_measurement(
        db,
        user.id,
        datetime.utcnow(),
        weight_kg=body.weight_kg,
    )
    return {"status": "ok", "id": m.id, "weight_kg": body.weight_kg}


@router.get("/weights/chart")
def weights_chart_png(
    telegram_id: int = Query(...),
    period: str = Query("month"),
    db: Session = Depends(get_db),
):
    from fastapi.responses import Response

    from app.infrastructure.charts.matplotlib_charts import weight_line_chart_png

    if period not in ("week", "month"):
        raise HTTPException(400, "period must be week or month")
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(404, "user not found")
    rows = list_user_measurements(db, user.id, limit=400)
    days = 56 if period == "week" else 366
    cutoff = date.today() - timedelta(days=days)
    pts: list[tuple[date, float]] = []
    for r in reversed(rows):
        if r.weight_kg is None:
            continue
        d = r.measured_at.date()
        if d >= cutoff:
            pts.append((d, float(r.weight_kg)))
    title = "Вес по неделям (точки измерений)" if period == "week" else "Вес по месяцу (точки измерений)"
    png = weight_line_chart_png(pts, title=title)
    return Response(content=png, media_type="image/png")


@router.delete("/weights/latest")
def undo_last_weight(telegram_id: int = Query(...), db: Session = Depends(get_db)):
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(404, "user not found")
    ok = delete_last_weight_measurement(db, user.id)
    if not ok:
        raise HTTPException(400, "nothing to delete")
    return {"status": "ok"}


@router.get("/weights/history")
def weight_history(
    telegram_id: int = Query(...),
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
):
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(404, "user not found")
    rows = list_user_measurements(db, user.id, limit=limit)
    return [
        {
            "id": r.id,
            "measured_at": r.measured_at.isoformat(),
            "weight_kg": r.weight_kg,
        }
        for r in rows
        if r.weight_kg is not None
    ]
