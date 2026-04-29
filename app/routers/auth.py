from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.profile import is_profile_completed
from app.auth.service import (
    login_user,
    login_with_telegram,
    login_with_telegram_oauth,
    logout_user,
    refresh_tokens,
    register_user,
)
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthTelegramCallbackRequest,
    AuthTelegramRequest,
    AuthTokenPair,
    TelegramAuthResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "sex": user.sex,
        "birth_date": user.birth_date,
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "goal": user.goal,
        "activity_level": user.activity_level,
        "target_weight_kg": user.target_weight_kg,
        "timezone": user.timezone,
        "telegram_id": user.telegram_id,
        "subscription_status": user.subscription_status,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "profile_completed": is_profile_completed(user),
    }


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


@router.post("/telegram/callback", response_model=TelegramAuthResponse)
def telegram_callback(payload: AuthTelegramCallbackRequest, db: Session = Depends(get_db)):
    user, tokens, is_new_user, profile_completed = login_with_telegram_oauth(db, payload)
    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "access_token_expires_in": tokens.access_token_expires_in,
        "user": _user_payload(user),
        "is_new_user": is_new_user,
        "profile_completed": profile_completed,
    }
