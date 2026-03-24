import base64
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.meal_service import analyze_photo, log_meal

router = APIRouter(prefix="/meals", tags=["meals"])


class AnalyzeBody(BaseModel):
    image_base64: str


class LogMealBody(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    image_base64: str
    telegram_file_id: str | None = None


@router.post("/analyze")
def analyze_meal_image(body: AnalyzeBody):
    """Analyze a food photo (base64). Returns ingredients + weights and optional nutrition."""
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")
    try:
        base64.b64decode(body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}") from e
    return analyze_photo(body.image_base64)


@router.post("/log")
def log_meal_from_photo(body: LogMealBody, db: Session = Depends(get_db)):
    """Analyze photo, save meal log for Telegram user. Used by the bot."""
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
