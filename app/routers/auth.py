from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.service import (
    login_user,
    login_with_telegram,
    login_with_telegram_oauth,
    login_with_yandex_oauth,
    logout_user,
    refresh_tokens,
    register_user,
)
from app.auth.user_me_payload import serialize_user_me
from app.db.session import get_db
from app.schemas.auth import (
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthTelegramCallbackRequest,
    AuthTelegramRequest,
    AuthTokenPair,
    AuthYandexCallbackRequest,
    OAuthAuthResponse,
    TelegramAuthResponse,
)
from app.services.nutrition_targets import create_or_update_active_nutrition_target
from app.services.weight_measurements import record_weight_measurement

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
    if user.weight_kg is not None:
        record_weight_measurement(db, user, weight_kg=float(user.weight_kg))
    else:
        create_or_update_active_nutrition_target(db, user)
        db.commit()
        db.refresh(user)
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
        "user": serialize_user_me(db, user),
        "is_new_user": is_new_user,
        "profile_completed": profile_completed,
    }


@router.post("/yandex/callback", response_model=OAuthAuthResponse)
def yandex_callback(payload: AuthYandexCallbackRequest, db: Session = Depends(get_db)):
    user, tokens, is_new_user, profile_completed = login_with_yandex_oauth(db, payload)
    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "access_token_expires_in": tokens.access_token_expires_in,
        "user": serialize_user_me(db, user),
        "is_new_user": is_new_user,
        "profile_completed": profile_completed,
    }
