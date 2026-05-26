"""User supplement additives and intakes (JWT /users/me)."""

from __future__ import annotations

import base64
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.db.nutrition_columns import MEAL_ITEM_NUTRITION_KEYS
from app.db.session import get_db
from app.infrastructure.storage.additive_photo_storage import save_additive_photo_pair
from app.schemas.additives import (
    AdditiveAnalyzeRequest,
    AdditiveAnalyzeResponse,
    AdditiveCreateRequest,
    AdditiveIntakeCreateRequest,
    AdditiveIntakeListResponse,
    AdditiveIntakeResponse,
    AdditiveListResponse,
    AdditiveResponse,
    AdditiveUpdateRequest,
    NutrientFieldResponse,
    WaterIntakeCreateRequest,
)
from app.services.additive_ai import analyze_additive_label_from_image_base64
from app.services.additives import (
    create_user_additive,
    delete_user_additive_intake,
    get_user_additive,
    list_user_additive_intakes_for_local_date,
    list_user_additives,
    record_additive_intake,
    record_water_intake,
    soft_delete_user_additive,
    update_user_additive,
)

router = APIRouter(prefix="/users/me", tags=["user-additives"])

_MAX_IMAGE_BYTES = 15 * 1024 * 1024
_MAX_SERVINGS = 100
_MAX_WATER_ML = 5000

_NUTRIENT_LABEL_OVERRIDES: dict[str, str] = {
    "calories": "Calories",
    "protein_g": "Protein",
    "fat_g": "Fat",
    "carbs_g": "Carbs",
    "fiber_g": "Fiber",
    "sugar_g": "Sugar",
    "sodium_mg": "Sodium",
    "saturated_fat_g": "Saturated fat",
    "water_g": "Water",
    "vitamin_c_mg": "Vitamin C",
    "vitamin_d_iu": "Vitamin D",
    "vitamin_e_mg": "Vitamin E",
    "vitamin_k_mcg": "Vitamin K",
    "vitamin_b6_mg": "Vitamin B6",
    "vitamin_b12_mcg": "Vitamin B12",
    "calcium_mg": "Calcium",
    "iron_mg": "Iron",
    "magnesium_mg": "Magnesium",
    "potassium_mg": "Potassium",
    "zinc_mg": "Zinc",
}


def _nutrient_label(key: str) -> str:
    if key in _NUTRIENT_LABEL_OVERRIDES:
        return _NUTRIENT_LABEL_OVERRIDES[key]
    parts = key.rsplit("_", 1)
    if len(parts) == 2:
        name, _unit = parts
        return name.replace("_", " ").title()
    return key.replace("_", " ").title()


def _nutrient_unit(key: str) -> str:
    if key == "calories":
        return "kcal"
    if key.endswith("_mg"):
        return "mg"
    if key.endswith("_mcg"):
        return "mcg"
    if key.endswith("_iu"):
        return "IU"
    if key.endswith("_g"):
        return "g"
    return ""


def _decode_image_base64(image_base64: str) -> bytes:
    if not image_base64:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="image_base64 is required")
    try:
        raw = base64.b64decode(image_base64, validate=True)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid base64: {e}") from e
    if len(raw) > _MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image too large (max 15 MB)")
    return raw


def _save_photo_from_base64(image_base64: str, user_id: int) -> dict[str, str]:
    raw = _decode_image_base64(image_base64)
    try:
        return save_additive_photo_pair(raw, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/additives/nutrient-fields", response_model=list[NutrientFieldResponse])
def get_additive_nutrient_fields(
    current_user: User = Depends(get_current_user),
):
    return [
        NutrientFieldResponse(key=key, label=_nutrient_label(key), unit=_nutrient_unit(key))
        for key in MEAL_ITEM_NUTRITION_KEYS
    ]


@router.post("/additives/analyze", response_model=AdditiveAnalyzeResponse)
def analyze_additive_label(
    body: AdditiveAnalyzeRequest,
    current_user: User = Depends(get_current_user),
):
    # TODO: optional AI feature usage limits
    _ = current_user
    _decode_image_base64(body.image_base64)
    result = analyze_additive_label_from_image_base64(body.image_base64)
    return AdditiveAnalyzeResponse(**result)


@router.post("/additives", response_model=AdditiveResponse, status_code=status.HTTP_201_CREATED)
def create_additive(
    body: AdditiveCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    name = (body.additive_name or "").strip()
    if not name or len(name) > 255:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="additive_name is required (max 255)")

    photo_large = None
    photo_thumb = None
    if body.image_base64:
        paths = _save_photo_from_base64(body.image_base64, current_user.id)
        photo_large = paths["photo_large"]
        photo_thumb = paths["photo_thumb"]

    row = create_user_additive(
        db,
        current_user.id,
        additive_name=name,
        serving_label=body.serving_label,
        serving_size_g=body.serving_size_g,
        nutrients=body.nutrients,
        photo_large=photo_large,
        photo_thumb=photo_thumb,
    )
    return AdditiveResponse.from_orm_row(row)


@router.get("/additives", response_model=AdditiveListResponse)
def list_additives(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = list_user_additives(db, current_user.id)
    return AdditiveListResponse(items=[AdditiveResponse.from_orm_row(r) for r in rows])


@router.get("/additives/{additive_id}", response_model=AdditiveResponse)
def get_additive(
    additive_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = get_user_additive(db, current_user.id, additive_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Additive not found")
    return AdditiveResponse.from_orm_row(row)


@router.patch("/additives/{additive_id}", response_model=AdditiveResponse)
def patch_additive(
    additive_id: int,
    body: AdditiveUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload: dict = {}
    if body.additive_name is not None:
        name = body.additive_name.strip()
        if not name or len(name) > 255:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="additive_name invalid")
        payload["additive_name"] = name
    if body.serving_label is not None:
        payload["serving_label"] = body.serving_label
    if body.serving_size_g is not None:
        payload["serving_size_g"] = body.serving_size_g
    if body.nutrients is not None:
        payload["nutrients"] = body.nutrients
    if body.image_base64:
        paths = _save_photo_from_base64(body.image_base64, current_user.id)
        payload["photo_large"] = paths["photo_large"]
        payload["photo_thumb"] = paths["photo_thumb"]

    row = update_user_additive(db, current_user.id, additive_id, payload)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Additive not found")
    return AdditiveResponse.from_orm_row(row)


@router.delete("/additives/{additive_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_additive(
    additive_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not soft_delete_user_additive(db, current_user.id, additive_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Additive not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/additive-intakes", response_model=AdditiveIntakeResponse, status_code=status.HTTP_201_CREATED)
def create_additive_intake(
    body: AdditiveIntakeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.servings_count <= 0 or body.servings_count > _MAX_SERVINGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"servings_count must be between 0 and {_MAX_SERVINGS}",
        )
    try:
        row = record_additive_intake(
            db,
            current_user,
            body.additive_id,
            body.servings_count,
            intake_local_date=body.intake_local_date,
            intake_local_time=body.intake_local_time,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return AdditiveIntakeResponse.from_orm_row(row, current_user)


@router.get("/additive-intakes/day", response_model=AdditiveIntakeListResponse)
def get_additive_intakes_for_day(
    date_q: date = Query(..., alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = list_user_additive_intakes_for_local_date(db, current_user, date_q)
    return AdditiveIntakeListResponse(
        date=date_q,
        items=[AdditiveIntakeResponse.from_orm_row(r, current_user) for r in rows],
    )


@router.delete("/additive-intakes/{intake_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_additive_intake(
    intake_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not delete_user_additive_intake(db, current_user.id, intake_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/water-intakes", response_model=AdditiveIntakeResponse, status_code=status.HTTP_201_CREATED)
def create_water_intake(
    body: WaterIntakeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.amount_ml <= 0 or body.amount_ml > _MAX_WATER_ML:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"amount_ml must be between 0 and {_MAX_WATER_ML}",
        )
    try:
        row = record_water_intake(
            db,
            current_user,
            amount_ml=body.amount_ml,
            intake_local_date=body.intake_local_date,
            intake_local_time=body.intake_local_time,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return AdditiveIntakeResponse.from_orm_row(row, current_user)
