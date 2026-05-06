from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from starlette.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import hash_password
from app.auth.user_me_payload import serialize_user_me
from app.db.models import Allergen, User
from app.db.repository import create_meal, delete_meal_for_user, list_meals_for_user_local_date, list_user_measurements
from app.db.session import get_db
from app.schemas.auth import (
    LabelAnalysisResponse,
    MyNutritionTargetResponse,
    NutritionTargetResponse,
    ProfilePatchRequest,
    UserMeResponse,
    WeightMeasurementCreateRequest,
    WeightMeasurementPoint,
    WeightMeasurementResponse,
    WeightMeasurementsResponse,
    WebMealSaveRequest,
    WebMealSaveResponse,
    WebMealsDayResponse,
)
from app.schemas.diary import DiarySnapshotResponse
from app.services.diary_snapshot import _resolve_tz, build_diary_snapshot
from app.services.web_meals_day import build_web_meal_day_row
from app.core.use_cases.meal_analysis import build_meal_item_specs_from_ingredients, resolve_meal_photo_urls_for_save
from app.services.ingredient_checker import analyze_label_from_image_bytes, format_label_result_for_telegram
from app.services.nutrition_targets import (
    create_or_update_active_nutrition_target,
    get_active_nutrition_target,
    get_nutrition_target_for_range,
)
from app.services.weight_measurements import record_weight_measurement

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


@router.post("/me/meals/save", response_model=WebMealSaveResponse)
def save_my_meal(
    body: WebMealSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Запись приёма в дневник для пользователя из JWT (как /meals/save по telegram_id)."""
    ingredients: dict[str, Any] = body.ingredients or {}
    if not ingredients:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="ingredients required")
    items = build_meal_item_specs_from_ingredients(ingredients)
    lg, th = resolve_meal_photo_urls_for_save(
        current_user.id,
        image_base64=body.image_base64,
        meal_photo_large=body.meal_photo_large,
        meal_photo_thumb=body.meal_photo_thumb,
    )
    create_meal(
        db,
        current_user.id,
        source_type=body.source_type or "photo",
        telegram_file_id=body.telegram_file_id,
        prediction=body.prediction,
        user_text=body.user_text,
        meal_photo_large=lg,
        meal_photo_thumb=th,
        items=items,
    )
    return WebMealSaveResponse(status="success")


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_user_me(db, current_user)


@router.get("/me/diary", response_model=DiarySnapshotResponse)
def get_my_diary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Сводка для страницы «Дневник»: последние приёмы, неделя, сегодня, вес."""
    return build_diary_snapshot(db, current_user)


@router.get("/me/meals/day", response_model=WebMealsDayResponse)
def get_my_meals_for_day(
    date_q: date = Query(..., alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Все приёмы за календарный день в часовом поясе профиля (query `date=YYYY-MM-DD`)."""
    tz = _resolve_tz(current_user)
    meals = list_meals_for_user_local_date(db, current_user.id, date_q, tz)
    rows = [build_web_meal_day_row(m, current_user) for m in meals]
    return WebMealsDayResponse(date=date_q, items=rows)


@router.delete("/me/meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not delete_meal_for_user(db, meal_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приём не найден")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me/nutrition-target", response_model=MyNutritionTargetResponse)
def get_my_nutrition_target(
    date_q: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if date_q is None:
        target = get_active_nutrition_target(db, user_id=current_user.id)
    else:
        tz = _resolve_tz(current_user)
        start_local = datetime.combine(date_q, datetime.min.time(), tzinfo=tz)
        end_local = start_local + timedelta(days=1)
        start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
        target = get_nutrition_target_for_range(
            db,
            user_id=current_user.id,
            range_start=start_utc,
            range_end=end_utc,
        )
    nt = NutritionTargetResponse.model_validate(target, from_attributes=True) if target is not None else None
    return {"nutrition_target": nt}


def _weight_history_cutoff(period: str) -> datetime | None:
    if period == "1m":
        return datetime.utcnow() - timedelta(days=30)
    if period == "3m":
        return datetime.utcnow() - timedelta(days=90)
    if period == "6m":
        return datetime.utcnow() - timedelta(days=180)
    if period == "1y":
        return datetime.utcnow() - timedelta(days=365)
    if period == "all":
        return None
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="period must be one of: 1m, 3m, 6m, 1y, all",
    )


@router.post("/me/measurements", response_model=WeightMeasurementResponse)
def add_my_weight_measurement(
    payload: WeightMeasurementCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    measurement, target = record_weight_measurement(
        db,
        current_user,
        weight_kg=payload.weight_kg,
        waist_cm=payload.waist_cm,
        body_fat_percent=payload.body_fat_percent,
        notes=payload.notes,
    )
    return WeightMeasurementResponse(
        id=measurement.id,
        measured_at=measurement.measured_at,
        weight_kg=float(measurement.weight_kg),
        waist_cm=measurement.waist_cm,
        body_fat_percent=measurement.body_fat_percent,
        notes=measurement.notes,
        nutrition_target=NutritionTargetResponse.model_validate(target, from_attributes=True) if target else None,
    )


@router.get("/me/measurements", response_model=WeightMeasurementsResponse)
def get_my_weight_measurements(
    period: str = Query("3m"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cutoff = _weight_history_cutoff(period)
    rows = list_user_measurements(db, current_user.id, limit=1000)
    points: list[WeightMeasurementPoint] = []
    for row in reversed(rows):
        if row.weight_kg is None:
            continue
        if cutoff is not None and row.measured_at < cutoff:
            continue
        points.append(
            WeightMeasurementPoint(
                id=row.id,
                measured_at=row.measured_at,
                weight_kg=float(row.weight_kg),
                waist_cm=row.waist_cm,
                body_fat_percent=row.body_fat_percent,
                notes=row.notes,
            )
        )
    return WeightMeasurementsResponse(period=period, items=points)


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
