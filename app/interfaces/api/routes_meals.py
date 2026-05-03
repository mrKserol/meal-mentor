import base64
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.schemas import MealLogRequest
from app.core.use_cases.meal_analysis import (
    analyze_and_log_meal_legacy,
    analyze_meal_from_image_base64,
    analyze_meal_from_text,
    persist_meal_to_database,
)
from app.db.session import get_db
from app.db.repository import (
    delete_meal_for_user,
    get_meal_by_id_for_user,
    get_meals,
    get_user_by_telegram_id,
)
from app.core.use_cases.meal_item_edit import recalculate_meal_item_weight
from app.core.use_cases.meal_items_mutations import (
    add_meal_items_from_text_description,
    remove_meal_item,
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
    prediction: str | None = None
    user_text: str | None = None
    image_base64: str | None = None
    meal_photo_large: str | None = None
    meal_photo_thumb: str | None = None


class LogMealBody(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    image_base64: str
    telegram_file_id: str | None = None


class AddMealItemBody(BaseModel):
    telegram_id: int
    description: str


@router.post("/analyze")
def analyze_meal_image(body: AnalyzeBody):
    """Analyze a food photo (base64). Does not write to DB."""
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")
    try:
        base64.b64decode(body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}") from e
    return analyze_meal_from_image_base64(body.image_base64).to_api_dict()


@router.post("/analyze-text")
def analyze_meal_text(body: AnalyzeTextBody):
    """Analyze meal from free-text description. Does not write to DB."""
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    return analyze_meal_from_text(body.text.strip()).to_api_dict()


@router.post("/save")
def save_meal(body: SaveMealBody, db: Session = Depends(get_db)):
    """Save a confirmed meal to the database (after user tapped Yes)."""
    if not body.ingredients:
        raise HTTPException(status_code=400, detail="ingredients required")
    out = persist_meal_to_database(
        db,
        MealLogRequest(
            telegram_id=body.telegram_id,
            username=body.username,
            first_name=body.first_name,
            ingredients=body.ingredients,
            source_type=body.source_type,
            telegram_file_id=body.telegram_file_id,
            prediction=body.prediction,
            user_text=body.user_text,
            image_base64=body.image_base64,
            meal_photo_large=body.meal_photo_large,
            meal_photo_thumb=body.meal_photo_thumb,
        ),
    ).to_api_dict()
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
    return analyze_and_log_meal_legacy(
        db,
        telegram_id=body.telegram_id,
        username=body.username,
        image_base64=body.image_base64,
        telegram_file_id=body.telegram_file_id,
        first_name=body.first_name,
    )


def _absolute_url(request: Request, path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return str(request.base_url).rstrip("/") + (path if path.startswith("/") else "/" + path)


def _meal_to_json(meal, request: Request) -> dict[str, Any]:
    return {
        "id": meal.id,
        "meal_datetime": meal.meal_datetime.isoformat(),
        "source_type": meal.source_type,
        "telegram_file_id": meal.telegram_file_id,
        "prediction": meal.prediction,
        "user_text": meal.user_text,
        "meal_photo_large": meal.meal_photo_large,
        "meal_photo_thumb": meal.meal_photo_thumb,
        "meal_photo_large_url": _absolute_url(request, meal.meal_photo_large),
        "meal_photo_thumb_url": _absolute_url(request, meal.meal_photo_thumb),
        "items": [
            {
                "id": it.id,
                "item_name": it.item_name,
                "estimated_weight_g": it.estimated_weight_g,
                "nutrition": (
                    {
                        "calories": it.nutrition.calories,
                        "protein_g": it.nutrition.protein_g,
                        "fat_g": it.nutrition.fat_g,
                        "carbs_g": it.nutrition.carbs_g,
                        "fiber_g": it.nutrition.fiber_g,
                    }
                    if it.nutrition
                    else None
                ),
            }
            for it in meal.items
        ],
    }


@router.get("/list")
def meals_list(
    request: Request,
    telegram_id: int = Query(...),
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(404, "user not found")
    meals = get_meals(db, user.id, limit=min(limit, 50), offset=offset)
    return {"items": [_meal_to_json(m, request) for m in meals], "limit": limit, "offset": offset}


@router.get("/{meal_id}")
def meal_detail(
    request: Request,
    meal_id: int,
    telegram_id: int = Query(...),
    db: Session = Depends(get_db),
):
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(404, "user not found")
    meal = get_meal_by_id_for_user(db, meal_id, user.id)
    if not meal:
        raise HTTPException(404, "meal not found")
    return _meal_to_json(meal, request)


@router.delete("/{meal_id}")
def meal_delete(
    meal_id: int,
    telegram_id: int = Query(...),
    db: Session = Depends(get_db),
):
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(404, "user not found")
    ok = delete_meal_for_user(db, meal_id, user.id)
    if not ok:
        raise HTTPException(404, "meal not found")
    return {"status": "ok"}


@router.patch("/{meal_id}/items/{item_id}")
def meal_item_patch_weight(
    meal_id: int,
    item_id: int,
    telegram_id: int = Query(...),
    weight_g: int = Query(...),
    db: Session = Depends(get_db),
):
    if weight_g <= 0 or weight_g > 50000:
        raise HTTPException(400, "invalid weight_g")
    out = recalculate_meal_item_weight(db, telegram_id, meal_id, item_id, weight_g)
    if out.get("status") != "ok":
        raise HTTPException(400, out.get("error", "update failed"))
    return out


@router.delete("/{meal_id}/items/{item_id}")
def meal_item_delete_row(
    meal_id: int,
    item_id: int,
    telegram_id: int = Query(...),
    db: Session = Depends(get_db),
):
    out = remove_meal_item(db, telegram_id, meal_id, item_id)
    if out.get("status") != "ok":
        raise HTTPException(404, out.get("error", "not found"))
    return {"status": "ok"}


@router.post("/{meal_id}/items")
def meal_item_add_from_text(
    meal_id: int,
    body: AddMealItemBody,
    db: Session = Depends(get_db),
):
    if not body.description.strip():
        raise HTTPException(400, "description required")
    out = add_meal_items_from_text_description(db, body.telegram_id, meal_id, body.description)
    if out.get("status") != "ok":
        raise HTTPException(400, out.get("error", "failed"))
    return out
