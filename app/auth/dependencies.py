from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        user_id = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.status == "blocked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")
    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.status == "blocked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_curator_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.status == "blocked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")
    if current_user.role not in ("curator", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Curator access required")
    return current_user
