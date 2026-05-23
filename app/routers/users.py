import base64
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from starlette.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import hash_password
from app.auth.user_me_payload import serialize_user_me
from app.db.models import Allergen, User
from app.db.repository import create_meal, delete_meal_for_user, list_meals_for_user_local_date, list_user_measurements
from app.db.session import get_db
from app.core.config import FOOD_ALIASES_PATH
from app.infrastructure.nutrition.food_aliases import FoodAliasIndex
from app.infrastructure.nutrition.food_name_resolver import FoodNameResolver
from app.schemas.auth import (
    FoodNameResolveRequest,
    FoodNameResolveResponse,
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
    WebMealUpdateRequest,
    WebMealUpdateResponse,
    WebMealsDayResponse,
)
from app.schemas.diary import DiarySnapshotResponse
from app.services.diary_snapshot import _resolve_tz, build_diary_snapshot
from app.services.user_timezone import meal_datetime_for_local_date_at_current_time, parse_meal_local_datetime_iso
from app.schemas.additives import DayNutritionTotals
from app.services.additive_totals import day_additive_totals_response, sum_additive_intakes_for_local_date
from app.services.web_meals_day import build_web_meal_day_row
from app.core.use_cases.meal_analysis import (
    analyze_meal_from_image_and_text,
    analyze_meal_from_image_base64,
    analyze_meal_from_text,
    build_meal_item_specs_from_ingredients,
    resolve_meal_photo_urls_for_save,
)
from app.services.usage_limits import (
    check_label_analysis_limits,
    check_photo_recognition_limits,
    check_text_ai_limits,
    record_label_analysis_usage,
    record_photo_recognition_usage,
    record_text_ai_usage,
)
from app.core.use_cases.meal_update import update_meal_composition
from app.services.ingredient_checker import analyze_label_from_image_bytes, format_label_result_for_telegram
from app.services.nutrition_targets import (
    create_or_update_active_nutrition_target,
    get_active_nutrition_target,
    get_nutrition_target_for_range,
)
from app.services.entitlements import build_user_entitlements
from app.services.weight_measurements import record_weight_measurement

ALLOWED_LANGUAGE_CODES = frozenset({"ru", "en", "es", "de", "fr"})

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


class WebAnalyzeImageBody(BaseModel):
    image_base64: str


class WebAnalyzeTextBody(BaseModel):
    text: str


class WebAnalyzeImageTextBody(BaseModel):
    image_base64: str
    text: str
    previous_ingredients: dict[str, Any] | None = None
    previous_prediction: str | None = None


@router.post("/me/meals/analyze")
def analyze_my_meal_image(
    body: WebAnalyzeImageBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.image_base64:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="image_base64 is required")
    try:
        base64.b64decode(body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid base64: {e}") from e

    check_photo_recognition_limits(db, current_user)
    result = analyze_meal_from_image_base64(body.image_base64)
    payload = result.to_api_dict()
    if payload.get("status") == "success":
        record_photo_recognition_usage(db, current_user)
        payload.setdefault("prediction_language", current_user.language or "ru")
    return payload


@router.post("/me/meals/analyze-text")
def analyze_my_meal_text(
    body: WebAnalyzeTextBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required")

    check_text_ai_limits(db, current_user)
    result = analyze_meal_from_text(body.text.strip(), user_language=current_user.language or "ru")
    payload = result.to_api_dict()
    if payload.get("status") == "success":
        record_text_ai_usage(db, current_user)
        payload.setdefault("prediction_language", current_user.language or "ru")
    return payload


@router.post("/me/meals/analyze-image-text")
def analyze_my_meal_image_text(
    body: WebAnalyzeImageTextBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.image_base64:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="image_base64 is required")
    if not body.text or not body.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required")
    try:
        base64.b64decode(body.image_base64)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid base64: {e}") from e

    check_photo_recognition_limits(db, current_user)
    result = analyze_meal_from_image_and_text(
        body.image_base64,
        body.text.strip(),
        previous_ingredients=body.previous_ingredients,
        previous_prediction=body.previous_prediction,
    )
    payload = result.to_api_dict()
    if payload.get("status") == "success":
        record_photo_recognition_usage(db, current_user)
        payload.setdefault("prediction_language", current_user.language or "ru")
    return payload


@router.post("/me/ingredients/resolve", response_model=FoodNameResolveResponse)
def resolve_my_ingredient_name(
    body: FoodNameResolveRequest,
    current_user: User = Depends(get_current_user),
):
    """Resolve a user-typed ingredient name to canonical name for nutrition lookup."""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="name is required")

    user_lang = current_user.language or "ru"
    aliases = FoodAliasIndex(FOOD_ALIASES_PATH)
    resolver = FoodNameResolver(aliases)
    resolved = resolver.resolve(name, language=user_lang)

    if resolved is not None:
        display = resolved.display_name or name
        return FoodNameResolveResponse(
            status="success",
            input_name=name,
            canonical_name=resolved.canonical_name,
            display_name=display,
            language=user_lang,
            default_state=resolved.default_state,
            category=resolved.category,
            source=resolved.source,
            confidence=resolved.confidence,
        )

    return FoodNameResolveResponse(
        status="success",
        input_name=name,
        canonical_name=name,
        display_name=name,
        language=user_lang,
        default_state=body.state,
        source="input",
        confidence=0.0,
    )


@router.post("/me/analyze-label", response_model=LabelAnalysisResponse)
async def analyze_product_label(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """Анализ фото этикетки: тот же пайплайн, что и /check_ingredients в Telegram (promt3.txt + vision)."""
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

    check_label_analysis_limits(db, current_user)
    data = analyze_label_from_image_bytes(body)
    if data.get("status") == "ok":
        record_label_analysis_usage(db, current_user)
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
    meal_dt = datetime.utcnow()
    if body.meal_local_datetime:
        try:
            meal_dt = parse_meal_local_datetime_iso(current_user, body.meal_local_datetime)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    elif body.meal_local_date is not None:
        meal_dt = meal_datetime_for_local_date_at_current_time(current_user, body.meal_local_date)

    pred_lang = body.prediction_language or current_user.language or "ru"
    create_meal(
        db,
        current_user.id,
        source_type=body.source_type or "photo",
        telegram_file_id=body.telegram_file_id,
        prediction=body.prediction,
        prediction_translated=body.prediction_translated,
        prediction_language=pred_lang,
        user_text=body.user_text,
        meal_photo_large=lg,
        meal_photo_thumb=th,
        items=items,
        meal_datetime=meal_dt,
    )
    return WebMealSaveResponse(status="success")


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize_user_me(db, current_user)


@router.get("/me/entitlements")
def get_my_entitlements(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_user_entitlements(db, current_user)


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
    additive_raw = sum_additive_intakes_for_local_date(db, current_user, date_q)
    additive_totals = DayNutritionTotals(**day_additive_totals_response(additive_raw))
    return WebMealsDayResponse(date=date_q, items=rows, additive_totals=additive_totals)


@router.patch("/me/meals/{meal_id}", response_model=WebMealUpdateResponse)
def patch_my_meal(
    meal_id: int,
    body: WebMealUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Обновить состав и название существующего приёма."""
    pred_lang = body.prediction_language or current_user.language or "ru"
    out = update_meal_composition(
        db,
        current_user.id,
        meal_id,
        body.ingredients or {},
        prediction=body.prediction,
        prediction_translated=body.prediction_translated,
        prediction_language=pred_lang,
    )
    if out.get("status") != "ok":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=out.get("error") or "update failed",
        )
    return WebMealUpdateResponse(status="success")


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

    for field in ("sex", "birth_date", "height_cm", "weight_kg", "activity_level", "target_weight_kg"):
        if field in data:
            setattr(current_user, field, data[field])

    if "language" in data:
        lang = data["language"]
        if lang is not None:
            lang_norm = str(lang).strip().lower()
            if lang_norm not in ALLOWED_LANGUAGE_CODES:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown language: {lang}",
                )
            current_user.language = lang_norm

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
