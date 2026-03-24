import json
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    DailySummary,
    Meal,
    MealItem,
    MealItemNutrition,
    RecommendationsLog,
    User,
    UserMeasurement,
)


def get_or_create_user(
    db: Session,
    telegram_id: int,
    username: Optional[str] = None,
    *,
    first_name: Optional[str] = None,
    sex: Optional[str] = None,
    birth_date: Optional[date] = None,
    height_cm: Optional[int] = None,
    weight_kg: Optional[float] = None,
    goal: Optional[str] = None,
    activity_level: Optional[str] = None,
    timezone: Optional[str] = None,
) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        changed = False
        if username is not None and user.username != username:
            user.username = username
            changed = True
        for field, value in (
            ("first_name", first_name),
            ("sex", sex),
            ("birth_date", birth_date),
            ("height_cm", height_cm),
            ("weight_kg", weight_kg),
            ("goal", goal),
            ("activity_level", activity_level),
            ("timezone", timezone),
        ):
            if value is not None and getattr(user, field) != value:
                setattr(user, field, value)
                changed = True
        if changed:
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
        return user
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        sex=sex,
        birth_date=birth_date,
        height_cm=height_cm,
        weight_kg=weight_kg,
        goal=goal,
        activity_level=activity_level,
        timezone=timezone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_meal(
    db: Session,
    user_id: int,
    *,
    meal_type: Optional[str] = None,
    source_type: str = "photo",
    meal_datetime: Optional[datetime] = None,
    telegram_file_id: Optional[str] = None,
    notes: Optional[str] = None,
    items: Optional[list[dict[str, Any]]] = None,
) -> Meal:
    """
    Create Meal and nested MealItem + MealItemNutrition in one commit.

    Each element of `items` may contain:
      item_name (required), estimated_weight_g, quantity, confidence,
      raw_recognition_text,
      nutrition: dict with calories, protein_g, fat_g, carbs_g, fiber_g, sugar_g, sodium_mg
    """
    meal = Meal(
        user_id=user_id,
        telegram_file_id=telegram_file_id,
        meal_type=meal_type,
        source_type=source_type,
        meal_datetime=meal_datetime or datetime.utcnow(),
        notes=notes,
    )
    db.add(meal)
    db.flush()

    for spec in items or []:
        name = spec.get("item_name")
        if not name:
            continue
        item = MealItem(
            meal_id=meal.id,
            item_name=name,
            estimated_weight_g=spec.get("estimated_weight_g"),
            quantity=spec.get("quantity"),
            confidence=spec.get("confidence"),
            raw_recognition_text=spec.get("raw_recognition_text"),
        )
        db.add(item)
        db.flush()

        nut = spec.get("nutrition") or {}
        if any(
            nut.get(k) is not None
            for k in (
                "calories",
                "protein_g",
                "fat_g",
                "carbs_g",
                "fiber_g",
                "sugar_g",
                "sodium_mg",
            )
        ):
            db.add(
                MealItemNutrition(
                    meal_item_id=item.id,
                    calories=nut.get("calories"),
                    protein_g=nut.get("protein_g"),
                    fat_g=nut.get("fat_g"),
                    carbs_g=nut.get("carbs_g"),
                    fiber_g=nut.get("fiber_g"),
                    sugar_g=nut.get("sugar_g"),
                    sodium_mg=nut.get("sodium_mg"),
                )
            )

    db.commit()
    db.refresh(meal)
    return meal


def get_meals(
    db: Session,
    user_id: int,
    since: Optional[datetime] = None,
    limit: int = 100,
) -> list[Meal]:
    q = db.query(Meal).filter(Meal.user_id == user_id).order_by(Meal.meal_datetime.desc())
    if since is not None:
        q = q.filter(Meal.meal_datetime >= since)
    return q.limit(limit).all()


def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def upsert_daily_summary(
    db: Session,
    user_id: int,
    summary_date: date,
    *,
    total_calories: int = 0,
    total_protein_g: int = 0,
    total_fat_g: int = 0,
    total_carbs_g: int = 0,
    meal_count: int = 0,
) -> DailySummary:
    row = (
        db.query(DailySummary)
        .filter(
            DailySummary.user_id == user_id,
            DailySummary.date == summary_date,
        )
        .first()
    )
    if row:
        row.total_calories = total_calories
        row.total_protein_g = total_protein_g
        row.total_fat_g = total_fat_g
        row.total_carbs_g = total_carbs_g
        row.meal_count = meal_count
        row.updated_at = datetime.utcnow()
    else:
        row = DailySummary(
            user_id=user_id,
            date=summary_date,
            total_calories=total_calories,
            total_protein_g=total_protein_g,
            total_fat_g=total_fat_g,
            total_carbs_g=total_carbs_g,
            meal_count=meal_count,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_recommendation_log(
    db: Session,
    user_id: int,
    log_date: date,
    recommendation_text: str,
    reason: Optional[dict[str, Any]] = None,
) -> RecommendationsLog:
    row = RecommendationsLog(
        user_id=user_id,
        date=log_date,
        recommendation_text=recommendation_text,
        reason_json=json.dumps(reason, ensure_ascii=False) if reason is not None else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_user_measurement(
    db: Session,
    user_id: int,
    measured_at: datetime,
    *,
    weight_kg: Optional[float] = None,
    waist_cm: Optional[float] = None,
    body_fat_percent: Optional[float] = None,
    notes: Optional[str] = None,
) -> UserMeasurement:
    row = UserMeasurement(
        user_id=user_id,
        measured_at=measured_at,
        weight_kg=weight_kg,
        waist_cm=waist_cm,
        body_fat_percent=body_fat_percent,
        notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
