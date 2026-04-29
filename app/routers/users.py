from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.profile import is_profile_completed
from app.auth.dependencies import get_current_user
from app.auth.security import hash_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import ProfilePatchRequest, UserMeResponse

router = APIRouter(prefix="/users", tags=["users-web"])


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "first_name": current_user.first_name,
        "sex": current_user.sex,
        "birth_date": current_user.birth_date,
        "height_cm": current_user.height_cm,
        "weight_kg": current_user.weight_kg,
        "goal": current_user.goal,
        "activity_level": current_user.activity_level,
        "target_weight_kg": current_user.target_weight_kg,
        "timezone": current_user.timezone,
        "telegram_id": current_user.telegram_id,
        "subscription_status": current_user.subscription_status,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "profile_completed": is_profile_completed(current_user),
    }


@router.patch("/me/profile", response_model=UserMeResponse)
def patch_my_profile(
    payload: ProfilePatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)

    new_email = data.get("email")
    if new_email is not None and new_email != current_user.email:
        existing = db.query(User).filter(User.email == new_email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        current_user.email = new_email

    new_password = data.get("password")
    if new_password:
        current_user.hashed_password = hash_password(new_password)

    for field in ("sex", "birth_date", "height_cm", "weight_kg", "goal", "activity_level", "target_weight_kg"):
        if field in data:
            setattr(current_user, field, data[field])

    current_user.updated_at = datetime.utcnow()
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "first_name": current_user.first_name,
        "sex": current_user.sex,
        "birth_date": current_user.birth_date,
        "height_cm": current_user.height_cm,
        "weight_kg": current_user.weight_kg,
        "goal": current_user.goal,
        "activity_level": current_user.activity_level,
        "target_weight_kg": current_user.target_weight_kg,
        "timezone": current_user.timezone,
        "telegram_id": current_user.telegram_id,
        "subscription_status": current_user.subscription_status,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "profile_completed": is_profile_completed(current_user),
    }
