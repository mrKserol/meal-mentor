import base64
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.schemas import MealLogRequest
from app.core.use_cases.meal_analysis import (
    analyze_and_log_meal_legacy,
    analyze_meal_from_image_base64,
    analyze_meal_from_image_and_text,
    analyze_meal_from_text,
    persist_meal_to_database,
    recalculate_nutrition_from_ingredients,
)
from app.core.use_cases.meal_analysis_v2 import (
    analyze_meal_from_image_and_text_v2_usda,
    analyze_meal_from_image_base64_v2_usda,
    analyze_meal_from_text_v2_usda,
    persist_meal_to_database_v2_usda,
    recalculate_nutrition_from_ingredients_v2_usda,
)
from app.core.use_cases.nutrition_pipeline_selector import (
    NutritionPipelineVersion,
    get_global_nutrition_pipeline,
    resolve_user_nutrition_pipeline,
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
logger = logging.getLogger(__name__)


class AnalyzeBody(BaseModel):
    image_base64: str
    telegram_id: int | None = None
    pipeline_version: str | None = None
    comment: str | None = None
    previous_ingredients: dict[str, Any] | None = None
    previous_prediction: str | None = None
    correction: str | None = None
    correction_history: list[str] | None = None


class AnalyzeTextBody(BaseModel):
    text: str
    telegram_id: int | None = None
    pipeline_version: str | None = None
    previous_ingredients: dict[str, Any] | None = None
    previous_prediction: str | None = None
    correction: str | None = None
    correction_history: list[str] | None = None


class AnalyzeImageTextBody(BaseModel):
    image_base64: str
    text: str
    previous_ingredients: dict[str, Any] | None = None
    previous_prediction: str | None = None
    comment: str | None = None
    correction_history: list[str] | None = None
    telegram_id: int | None = None
    pipeline_version: str | None = None


class RecalculateNutritionBody(BaseModel):
    ingredients: dict[str, Any]
    telegram_id: int | None = None
    pipeline_version: str | None = None


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
    pipeline_version: str | None = None


class LogMealBody(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    image_base64: str
    telegram_file_id: str | None = None
    pipeline_version: str | None = None


class AddMealItemBody(BaseModel):
    telegram_id: int
    description: str


def _resolve_pipeline(
    db: Session,
    *,
    telegram_id: int | None = None,
    requested: str | None = None,
) -> str:
    if requested in (NutritionPipelineVersion.V1_CSV.value, NutritionPipelineVersion.V2_USDA.value):
        return requested
    if telegram_id:
        user = get_user_by_telegram_id(db, telegram_id)
        return resolve_user_nutrition_pipeline(db, user)
    return get_global_nutrition_pipeline(db)


def _with_pipeline(payload: dict[str, Any], pipeline: str) -> dict[str, Any]:
    payload["nutrition_pipeline"] = pipeline
    return payload


@router.post("/analyze")
def analyze_meal_image(body: AnalyzeBody, db: Session = Depends(get_db)):
    """Analyze a food photo (base64). Does not write to DB."""
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")
    try:
        base64.b64decode(body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}") from e
    pipeline = _resolve_pipeline(db, telegram_id=body.telegram_id, requested=body.pipeline_version)
    actual_pipeline = NutritionPipelineVersion.V1_CSV.value
    result = None
    correction = (body.correction or "").strip()
    if pipeline == NutritionPipelineVersion.V2_USDA.value:
        try:
            if correction:
                result = analyze_meal_from_image_and_text_v2_usda(
                    body.image_base64,
                    correction,
                    previous_ingredients=body.previous_ingredients,
                    previous_prediction=body.previous_prediction,
                    initial_comment=body.comment,
                    correction_history=body.correction_history,
                    db=db,
                )
            else:
                result = analyze_meal_from_image_base64_v2_usda(body.image_base64, db=db)
            if result.status == "success":
                actual_pipeline = NutritionPipelineVersion.V2_USDA.value
        except Exception:
            logger.exception("V2 USDA analyze failed, fallback to V1")
            result = None
    if result is None or result.status != "success":
        if correction:
            result = analyze_meal_from_image_and_text(
                body.image_base64,
                correction,
                previous_ingredients=body.previous_ingredients,
                previous_prediction=body.previous_prediction,
                initial_comment=body.comment,
                correction_history=body.correction_history,
            )
        else:
            result = analyze_meal_from_image_base64(body.image_base64, user_comment=body.comment)
    return _with_pipeline(result.to_api_dict(), actual_pipeline)


@router.post("/analyze-text")
def analyze_meal_text(body: AnalyzeTextBody, db: Session = Depends(get_db)):
    """Analyze meal from free-text description. Does not write to DB."""
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    pipeline = _resolve_pipeline(db, telegram_id=body.telegram_id, requested=body.pipeline_version)
    actual_pipeline = NutritionPipelineVersion.V1_CSV.value
    result = None
    if pipeline == NutritionPipelineVersion.V2_USDA.value:
        try:
            result = analyze_meal_from_text_v2_usda(
                body.text.strip(),
                previous_ingredients=body.previous_ingredients,
                previous_prediction=body.previous_prediction,
                correction=body.correction,
                correction_history=body.correction_history,
                db=db,
            )
            if result.status == "success":
                actual_pipeline = NutritionPipelineVersion.V2_USDA.value
        except Exception:
            logger.exception("V2 USDA text analyze failed, fallback to V1")
            result = None
    if result is None or result.status != "success":
        result = analyze_meal_from_text(
            body.text.strip(),
            previous_ingredients=body.previous_ingredients,
            previous_prediction=body.previous_prediction,
            correction=body.correction,
            correction_history=body.correction_history,
        )
    return _with_pipeline(result.to_api_dict(), actual_pipeline)


@router.post("/analyze-image-text")
def analyze_meal_image_text(body: AnalyzeImageTextBody, db: Session = Depends(get_db)):
    """
    Analyze meal using original photo + user correction text.
    Does not write to DB.
    """
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")

    if not body.text or not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")

    try:
        base64.b64decode(body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}") from e

    pipeline = _resolve_pipeline(db, telegram_id=body.telegram_id, requested=body.pipeline_version)
    actual_pipeline = NutritionPipelineVersion.V1_CSV.value
    result = None
    if pipeline == NutritionPipelineVersion.V2_USDA.value:
        try:
            result = analyze_meal_from_image_and_text_v2_usda(
                body.image_base64,
                body.text.strip(),
                previous_ingredients=body.previous_ingredients,
                previous_prediction=body.previous_prediction,
                initial_comment=body.comment,
                correction_history=body.correction_history,
                db=db,
            )
            if result.status == "success":
                actual_pipeline = NutritionPipelineVersion.V2_USDA.value
        except Exception:
            logger.exception("V2 USDA image+text analyze failed, fallback to V1")
            result = None
    if result is None or result.status != "success":
        result = analyze_meal_from_image_and_text(
            body.image_base64,
            body.text.strip(),
            previous_ingredients=body.previous_ingredients,
            previous_prediction=body.previous_prediction,
            initial_comment=body.comment,
            correction_history=body.correction_history,
        )
    return _with_pipeline(result.to_api_dict(), actual_pipeline)


@router.post("/recalculate")
def recalculate_meal_nutrition(body: RecalculateNutritionBody, db: Session = Depends(get_db)):
    """
    Recalculate nutrition from edited ingredients without AI request.
    Used by web add-meal confirmation UI.
    """
    if not body.ingredients:
        return _with_pipeline({
            "status": "success",
            "ingredients": {},
            "nutrition": {
                "calories": 0,
                "proteins": 0,
                "fats": 0,
                "carbohydrates": 0,
            },
        }, NutritionPipelineVersion.V1_CSV.value)

    pipeline = _resolve_pipeline(db, telegram_id=body.telegram_id, requested=body.pipeline_version)
    actual_pipeline = NutritionPipelineVersion.V1_CSV.value
    result = None
    if pipeline == NutritionPipelineVersion.V2_USDA.value:
        try:
            result = recalculate_nutrition_from_ingredients_v2_usda(body.ingredients, db=db)
            if result.status == "success":
                actual_pipeline = NutritionPipelineVersion.V2_USDA.value
        except Exception:
            logger.exception("V2 USDA recalculate failed, fallback to V1")
            result = None
    if result is None or result.status != "success":
        result = recalculate_nutrition_from_ingredients(body.ingredients)
    return _with_pipeline(result.to_api_dict(), actual_pipeline)


@router.post("/save")
def save_meal(body: SaveMealBody, db: Session = Depends(get_db)):
    """Save a confirmed meal to the database (after user tapped Yes)."""
    if not body.ingredients:
        raise HTTPException(status_code=400, detail="ingredients required")
    pipeline = _resolve_pipeline(db, telegram_id=body.telegram_id, requested=body.pipeline_version)
    req = MealLogRequest(
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
    )
    actual_pipeline = NutritionPipelineVersion.V1_CSV.value
    if pipeline == NutritionPipelineVersion.V2_USDA.value:
        out = persist_meal_to_database_v2_usda(db, req).to_api_dict()
        if out.get("status") == "success":
            return _with_pipeline(out, NutritionPipelineVersion.V2_USDA.value)
        logger.warning("V2 USDA save failed, fallback to V1: %s", out.get("error"))
    out = persist_meal_to_database(
        db,
        req,
    ).to_api_dict()
    if out.get("status") != "success":
        raise HTTPException(status_code=400, detail=out.get("error", "save failed"))
    return _with_pipeline(out, actual_pipeline)


@router.post("/log")
def log_meal_from_photo(body: LogMealBody, db: Session = Depends(get_db)):
    """Legacy: analyze + save in one request."""
    if not body.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")
    try:
        base64.b64decode(body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {e}") from e
    pipeline = _resolve_pipeline(db, telegram_id=body.telegram_id, requested=body.pipeline_version)
    if pipeline == NutritionPipelineVersion.V2_USDA.value:
        try:
            analyzed = analyze_meal_from_image_base64_v2_usda(body.image_base64, db=db)
            payload = analyzed.to_api_dict()
            if payload.get("status") == "success":
                save = persist_meal_to_database_v2_usda(
                    db,
                    MealLogRequest(
                        telegram_id=body.telegram_id,
                        username=body.username,
                        first_name=body.first_name,
                        ingredients=payload.get("ingredients") or {},
                        source_type="photo",
                        telegram_file_id=body.telegram_file_id,
                        prediction=payload.get("prediction"),
                        prediction_translated=payload.get("prediction_translated"),
                        prediction_language=payload.get("prediction_language"),
                        image_base64=body.image_base64,
                    ),
                )
                save_d = save.to_api_dict()
                if save_d.get("status") == "success":
                    return _with_pipeline(payload, NutritionPipelineVersion.V2_USDA.value)
        except Exception:
            logger.exception("V2 USDA log failed, fallback to V1")
    payload = analyze_and_log_meal_legacy(
        db,
        telegram_id=body.telegram_id,
        username=body.username,
        image_base64=body.image_base64,
        telegram_file_id=body.telegram_file_id,
        first_name=body.first_name,
    )
    return _with_pipeline(payload, NutritionPipelineVersion.V1_CSV.value)


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
