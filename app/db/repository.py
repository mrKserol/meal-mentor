import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import User, MealLog


def get_or_create_user(db: Session, telegram_id: int, username: Optional[str] = None) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        if username is not None and user.username != username:
            user.username = username
            db.commit()
            db.refresh(user)
        return user
    user = User(telegram_id=telegram_id, username=username)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_meal_log(
    db: Session,
    user_id: int,
    ingredients: dict,
    nutrition: dict,
    telegram_file_id: Optional[str] = None,
) -> MealLog:
    log = MealLog(
        user_id=user_id,
        telegram_file_id=telegram_file_id,
        ingredients_json=json.dumps(ingredients, ensure_ascii=False),
        nutrition_json=json.dumps(nutrition, ensure_ascii=False),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_meal_logs(
    db: Session,
    user_id: int,
    since: Optional[datetime] = None,
    limit: int = 100,
) -> list[MealLog]:
    q = db.query(MealLog).filter(MealLog.user_id == user_id).order_by(MealLog.created_at.desc())
    if since is not None:
        q = q.filter(MealLog.created_at >= since)
    return q.limit(limit).all()


def get_user_by_telegram_id(db: Session, telegram_id: int) -> Optional[User]:
    return db.query(User).filter(User.telegram_id == telegram_id).first()
