from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.service import login_user, logout_user, refresh_tokens, register_user
from app.db.session import get_db
from app.schemas.auth import (
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthTokenPair,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthTokenPair, status_code=status.HTTP_201_CREATED)
def register(payload: AuthRegisterRequest, db: Session = Depends(get_db)):
    user = register_user(
        db,
        email=payload.email,
        username=payload.username,
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
