import json
import zoneinfo
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    DailySummary,
    Meal,
    MealItem,
    MealItemNutrition,
    RecommendationsLog,
    Subscription,
    User,
    UserMeasurement,
)
from app.db.nutrition_columns import MEAL_ITEM_NUTRITION_KEYS
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
    target_weight_kg: Optional[float] = None,
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
            ("target_weight_kg", target_weight_kg),
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
        target_weight_kg=target_weight_kg,
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
    prediction: Optional[str] = None,
    user_text: Optional[str] = None,
    meal_photo_large: Optional[str] = None,
    meal_photo_thumb: Optional[str] = None,
    items: Optional[list[dict[str, Any]]] = None,
) -> Meal:
    """
    Create Meal and nested MealItem + MealItemNutrition in one commit.

    nutrition dict may include any keys from MEAL_ITEM_NUTRITION_KEYS.
    """
    meal = Meal(
        user_id=user_id,
        telegram_file_id=telegram_file_id,
        meal_type=meal_type,
        source_type=source_type,
        meal_datetime=meal_datetime or datetime.utcnow(),
        notes=notes,
        prediction=prediction,
        user_text=user_text,
        meal_photo_large=meal_photo_large,
        meal_photo_thumb=meal_photo_thumb,
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
            ingredient_state=spec.get("ingredient_state"),
            estimated_weight_g=spec.get("estimated_weight_g"),
            quantity=spec.get("quantity"),
            confidence=spec.get("confidence"),
            raw_recognition_text=spec.get("raw_recognition_text"),
        )
        db.add(item)
        db.flush()

        nut = spec.get("nutrition") or {}
        payload = {k: nut[k] for k in MEAL_ITEM_NUTRITION_KEYS if k in nut and nut[k] is not None}
        if payload:
            db.add(MealItemNutrition(meal_item_id=item.id, **payload))

    db.commit()
    db.refresh(meal)
    return meal


def get_meals(
    db: Session,
    user_id: int,
    since: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Meal]:
    q = db.query(Meal).filter(Meal.user_id == user_id).order_by(Meal.meal_datetime.desc())
    if since is not None:
        q = q.filter(Meal.meal_datetime >= since)
    return q.offset(offset).limit(limit).all()


def get_meal_by_id_for_user(db: Session, meal_id: int, user_id: int) -> Optional[Meal]:
    return (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.id == meal_id, Meal.user_id == user_id)
        .first()
    )


def delete_meal_for_user(db: Session, meal_id: int, user_id: int) -> bool:
    meal = db.query(Meal).filter(Meal.id == meal_id, Meal.user_id == user_id).first()
    if not meal:
        return False
    db.delete(meal)
    db.commit()
    return True


def list_meals_for_user_local_date(
    db: Session,
    user_id: int,
    d: date,
    tz: zoneinfo.ZoneInfo,
) -> list[Meal]:
    """Приёмы за календарный день `d` в часовом поясе `tz` (meal_datetime хранится как UTC-naive)."""
    start_local = datetime.combine(d, datetime.min.time(), tzinfo=tz)
    end_local = datetime.combine(d + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user_id, Meal.meal_datetime >= start_utc, Meal.meal_datetime < end_utc)
        .order_by(Meal.meal_datetime.desc())
        .all()
    )


def update_meal_item_weight(
    db: Session,
    meal_id: int,
    user_id: int,
    item_id: int,
    estimated_weight_g: int,
    *,
    nutrition: Optional[dict[str, Any]] = None,
) -> bool:
    """Update one line item weight and optional full nutrition row (caller supplies recalculated dict)."""
    meal = db.query(Meal).filter(Meal.id == meal_id, Meal.user_id == user_id).first()
    if not meal:
        return False
    item = db.query(MealItem).filter(MealItem.id == item_id, MealItem.meal_id == meal_id).first()
    if not item:
        return False
    item.estimated_weight_g = estimated_weight_g
    if nutrition is not None:
        n = item.nutrition
        if n is None:
            payload = {k: nutrition[k] for k in MEAL_ITEM_NUTRITION_KEYS if k in nutrition and nutrition[k] is not None}
            if payload:
                db.add(MealItemNutrition(meal_item_id=item.id, **payload))
        else:
            for k in MEAL_ITEM_NUTRITION_KEYS:
                if k in nutrition:
                    setattr(n, k, nutrition[k])
    db.commit()
    return True


def delete_meal_item_for_user(db: Session, meal_id: int, user_id: int, item_id: int) -> bool:
    meal = db.query(Meal).filter(Meal.id == meal_id, Meal.user_id == user_id).first()
    if not meal:
        return False
    item = db.query(MealItem).filter(MealItem.id == item_id, MealItem.meal_id == meal_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def append_meal_item_rows(
    db: Session,
    meal_id: int,
    user_id: int,
    items: list[dict[str, Any]],
) -> bool:
    """Append MealItem (+ nutrition) rows to an existing meal."""
    meal = db.query(Meal).filter(Meal.id == meal_id, Meal.user_id == user_id).first()
    if not meal:
        return False
    for spec in items or []:
        name = spec.get("item_name")
        if not name:
            continue
        row = MealItem(
            meal_id=meal.id,
            item_name=name,
            ingredient_state=spec.get("ingredient_state"),
            estimated_weight_g=spec.get("estimated_weight_g"),
            quantity=spec.get("quantity"),
            confidence=spec.get("confidence"),
            raw_recognition_text=spec.get("raw_recognition_text"),
        )
        db.add(row)
        db.flush()
        nut = spec.get("nutrition") or {}
        payload = {k: nut[k] for k in MEAL_ITEM_NUTRITION_KEYS if k in nut and nut[k] is not None}
        if payload:
            db.add(MealItemNutrition(meal_item_id=row.id, **payload))
    db.commit()
    return True


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
    commit: bool = True,
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
    db.flush()
    if weight_kg is not None:
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            u.weight_kg = weight_kg
            u.updated_at = datetime.utcnow()
    if commit:
        db.commit()
        db.refresh(row)
    return row


def list_user_measurements(
    db: Session,
    user_id: int,
    *,
    limit: int = 50,
) -> list[UserMeasurement]:
    return (
        db.query(UserMeasurement)
        .filter(UserMeasurement.user_id == user_id)
        .order_by(UserMeasurement.measured_at.desc())
        .limit(limit)
        .all()
    )


def delete_last_weight_measurement(db: Session, user_id: int) -> bool:
    """Remove most recent weight entry and set user.weight_kg to previous measurement if any."""
    rows = (
        db.query(UserMeasurement)
        .filter(UserMeasurement.user_id == user_id, UserMeasurement.weight_kg.isnot(None))
        .order_by(UserMeasurement.measured_at.desc())
        .limit(2)
        .all()
    )
    if not rows:
        return False
    db.delete(rows[0])
    u = db.query(User).filter(User.id == user_id).first()
    if u:
        if len(rows) > 1:
            u.weight_kg = rows[1].weight_kg
        else:
            u.weight_kg = None
        u.updated_at = datetime.utcnow()
    db.commit()
    return True


def get_active_subscription(db: Session, user_id: int) -> Optional[Subscription]:
    now = datetime.utcnow()
    return (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.ends_at.isnot(None),
            Subscription.ends_at > now,
        )
        .order_by(Subscription.ends_at.desc())
        .first()
    )


def create_subscription_stub(
    db: Session,
    user_id: int,
    plan: str,
    *,
    plan_id: int | None = None,
) -> Subscription:
    """Pending payment placeholder — flip to active when Robokassa webhook confirms."""
    row = Subscription(
        user_id=user_id,
        plan_id=plan_id,
        plan=plan,
        status="pending",
        provider="robokassa",
        payment_status="pending",
        external_payment_id=None,
        started_at=None,
        ends_at=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def activate_subscription_for_demo(
    db: Session,
    subscription_id: int,
    *,
    days: int,
) -> Optional[Subscription]:
    """Dev/demo: mark subscription active without payment (optional Telegram tariff tap)."""
    from datetime import timedelta

    row = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if not row:
        return None
    now = datetime.utcnow()
    row.status = "active"
    row.payment_status = "demo"
    row.started_at = now
    row.ends_at = now + timedelta(days=days)
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return row
