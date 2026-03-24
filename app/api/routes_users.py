from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repository import get_or_create_user

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    sex: str | None = None
    birth_date: date | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
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
    goal: str | None
    activity_level: str | None
    timezone: str | None

    class Config:
        from_attributes = True


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
        goal=data.goal,
        activity_level=data.activity_level,
        timezone=data.timezone,
    )
    return user
