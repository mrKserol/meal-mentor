from sqlalchemy.orm import Session

from app.auth.profile import is_profile_completed
from app.db.models import User
from app.schemas.auth import NutritionTargetResponse
from app.services.nutrition_targets import get_active_nutrition_target


def serialize_user_me(db: Session, user: User) -> dict:
    active = get_active_nutrition_target(db, user_id=user.id)
    nutrition = (
        NutritionTargetResponse.model_validate(active, from_attributes=True) if active is not None else None
    )
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
        "language": user.language or "ru",
        "telegram_id": user.telegram_id,
        "role": user.role,
        "status": user.status,
        "subscription_status": user.subscription_status,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "profile_completed": is_profile_completed(user),
        "nutrition_target": nutrition.model_dump() if nutrition is not None else None,
        "allergens": sorted(a.allergen_key for a in user.allergens),
    }
