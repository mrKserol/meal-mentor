import base64
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.meal_service import (
    analyze_photo,
    analyze_text,
    log_meal,
    save_meal_to_db,
)

router = APIRouter(prefix="/meals", tags=["meals"])


class AnalyzeBody(BaseModel):
    image_base64: str


class AnalyzeTextBody(BaseModel):
    text: str


class SaveMealBody(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    ingredients: dict[str, Any]
    source_type: str = "photo"
    telegram_file_id: str | None = None


class LogMealBody(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    image_base64: str
    telegram_file_id: str | None = None


@router.post("/analyze")
def analyze_meal_image(body: AnalyzeBody):
    """Analyze a food photo (base64). Does not write to DB."""
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")
    try:
        base64.b64decode(body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}") from e
    return analyze_photo(body.image_base64)


@router.post("/analyze-text")
def analyze_meal_text(body: AnalyzeTextBody):
    """Analyze meal from free-text description. Does not write to DB."""
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    return analyze_text(body.text.strip())


@router.post("/save")
def save_meal(body: SaveMealBody, db: Session = Depends(get_db)):
    """Save a confirmed meal to the database (after user tapped Yes)."""
    if not body.ingredients:
        raise HTTPException(status_code=400, detail="ingredients required")
    out = save_meal_to_db(
        db,
        telegram_id=body.telegram_id,
        username=body.username,
        ingredients=body.ingredients,
        source_type=body.source_type,
        telegram_file_id=body.telegram_file_id,
        first_name=body.first_name,
    )
    if out.get("status") != "success":
        raise HTTPException(status_code=400, detail=out.get("error", "save failed"))
    return out


@router.post("/log")
def log_meal_from_photo(body: LogMealBody, db: Session = Depends(get_db)):
    """Legacy: analyze + save in one request."""
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")
    try:
        base64.b64decode(body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}") from e
    return log_meal(
        db,
        telegram_id=body.telegram_id,
        username=body.username,
        image_base64=body.image_base64,
        telegram_file_id=body.telegram_file_id,
        first_name=body.first_name,
    )
