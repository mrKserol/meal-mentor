from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repository import get_or_create_user

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    telegram_id: int
    username: str | None = None


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None

    class Config:
        from_attributes = True


@router.post("/register", response_model=UserResponse)
def register_user(data: UserCreate, db: Session = Depends(get_db)):
    user = get_or_create_user(db, telegram_id=data.telegram_id, username=data.username)
    return user
