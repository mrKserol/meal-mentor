from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.service import login_user, login_with_telegram, logout_user, refresh_tokens, register_user
from app.db.session import get_db
from app.schemas.auth import (
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthTelegramRequest,
    AuthTokenPair,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthTokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)):
    user = register_user(
        db,
        telegram_username=payload.telegram_username,
        first_name=payload.first_name,
        sex=payload.sex,
        birth_date=payload.birth_date,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        goal=payload.goal,
        activity_level=payload.activity_level,
        target_weight_kg=payload.target_weight_kg,
        timezone=payload.timezone,
        email=payload.email,
        password=payload.password,
    )
    _, tokens = login_user(db, email=user.email, password=payload.password)
    return tokens


@router.post("/login", response_model=AuthTokenPair)
def login(payload: AuthLoginRequest, db: Session = Depends(get_db)):
    _, tokens = login_user(db, email=payload.email, password=payload.password)
    return tokens


@router.post("/refresh", response_model=AuthTokenPair)
def refresh(payload: AuthRefreshRequest, db: Session = Depends(get_db)):
    return refresh_tokens(db, refresh_token=payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: AuthLogoutRequest, db: Session = Depends(get_db)):
    logout_user(db, refresh_token=payload.refresh_token)


@router.post("/telegram", response_model=AuthTokenPair)
def telegram_login(payload: AuthTelegramRequest, db: Session = Depends(get_db)):
    _, tokens = login_with_telegram(db, payload)
    return tokens
