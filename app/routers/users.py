from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import hash_password
from app.auth.user_me_payload import serialize_user_me
from app.db.models import Allergen, User
from app.db.session import get_db
from app.schemas.auth import (
    LabelAnalysisResponse,
    MyNutritionTargetResponse,
    NutritionTargetResponse,
    ProfilePatchRequest,
    UserMeResponse,
)
from app.services.ingredient_checker import analyze_label_from_image_bytes, format_label_result_for_telegram
from app.services.nutrition_targets import (
    create_or_update_active_nutrition_target,
    get_active_nutrition_target,
)

ALLOWED_ALLERGEN_KEYS = frozenset(
    {
        "dairy",
        "eggs",
        "peanuts",
        "shellfish",
        "gluten",
        "fish",
        "soy",
        "tree_nuts",
        "citrus",
        "nightshades",
    }
)

router = APIRouter(prefix="/users", tags=["users-web"])

_MAX_LABEL_IMAGE_BYTES = 15 * 1024 * 1024


@router.post("/me/analyze-label", response_model=LabelAnalysisResponse)
async def analyze_product_label(
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
):
    """Анализ фото этикетки: тот же пайплайн, что и /check_ingredients в Telegram (promt3.txt + vision)."""
    _ = current_user
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Нужен файл изображения (JPEG, PNG и т.д.).",
        )
    body = await file.read()
    if not body:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Пустой файл.")
    if len(body) > _MAX_LABEL_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл слишком большой.")

    data = analyze_label_from_image_bytes(body)
    text = format_label_result_for_telegram(data)
    return LabelAnalysisResponse(text=text)


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_user_me(db, current_user)


@router.get("/me/nutrition-target", response_model=MyNutritionTargetResponse)
def get_my_nutrition_target(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    active = get_active_nutrition_target(db, user_id=current_user.id)
    nt = NutritionTargetResponse.model_validate(active, from_attributes=True) if active is not None else None
    return {"nutrition_target": nt}


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

    if "allergens" in data:
        incoming_allergens = data["allergens"] or []
        normalized_allergens: list[str] = []
        for key in incoming_allergens:
            if key not in ALLOWED_ALLERGEN_KEYS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown allergen: {key}",
                )
            if key not in normalized_allergens:
                normalized_allergens.append(key)

        db.query(Allergen).filter(Allergen.user_id == current_user.id).delete(synchronize_session=False)

        for key in normalized_allergens:
            db.add(Allergen(user_id=current_user.id, allergen_key=key))

    current_user.updated_at = datetime.utcnow()
    db.add(current_user)

    create_or_update_active_nutrition_target(db, current_user)

    db.commit()
    db.refresh(current_user)
    db.expire(current_user, ["allergens"])

    return serialize_user_me(db, current_user)
