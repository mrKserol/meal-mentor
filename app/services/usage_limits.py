"""Usage counters and limit checks for AI-related features."""

from datetime import date, datetime
import zoneinfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import FeatureUsage, User
from app.services.feature_access import get_feature_limit, is_feature_enabled

LIMIT_DENIED_MESSAGES: dict[str, str] = {
    "food_photo_recognition_enabled": "Распознавание еды по фото недоступно на вашем тарифе.",
    "label_analysis_enabled": "Анализ этикеток недоступен на вашем тарифе.",
    "ai_chat_enabled": "ИИ-чат недоступен на вашем тарифе.",
    "daily_photo_recognition_limit": "Дневной лимит распознаваний фото исчерпан для вашего тарифа.",
    "monthly_photo_recognition_limit": "Месячный лимит распознаваний фото исчерпан для вашего тарифа.",
    "monthly_label_analysis_limit": "Месячный лимит анализов этикеток исчерпан для вашего тарифа.",
    "daily_ai_requests_limit": "Дневной лимит ИИ-запросов исчерпан для вашего тарифа.",
    "daily_ai_chat_messages_limit": "Дневной лимит сообщений в ИИ-чате исчерпан для вашего тарифа.",
}


def _user_now(timezone: str | None) -> datetime:
    if timezone:
        try:
            return datetime.now(zoneinfo.ZoneInfo(timezone))
        except Exception:
            pass
    return datetime.utcnow()


def get_period_start(now: datetime, period_type: str, timezone: str | None = None) -> date:
    """daily: локальная дата пользователя; monthly: первое число месяца."""
    if timezone:
        try:
            now = now.astimezone(zoneinfo.ZoneInfo(timezone))
        except Exception:
            pass
    if period_type == "monthly":
        return date(now.year, now.month, 1)
    return now.date()


def get_usage_count(
    db: Session,
    user_id: int,
    feature_key: str,
    period_type: str,
    timezone: str | None = None,
) -> int:
    period_start = get_period_start(_user_now(timezone), period_type, timezone)
    row = (
        db.query(FeatureUsage)
        .filter(
            FeatureUsage.user_id == user_id,
            FeatureUsage.feature_key == feature_key,
            FeatureUsage.period_type == period_type,
            FeatureUsage.period_start == period_start,
        )
        .first()
    )
    return int(row.used_count) if row else 0


def increment_usage(
    db: Session,
    user_id: int,
    feature_key: str,
    period_type: str,
    amount: int = 1,
    timezone: str | None = None,
    commit: bool = True,
) -> None:
    period_start = get_period_start(_user_now(timezone), period_type, timezone)
    row = (
        db.query(FeatureUsage)
        .filter(
            FeatureUsage.user_id == user_id,
            FeatureUsage.feature_key == feature_key,
            FeatureUsage.period_type == period_type,
            FeatureUsage.period_start == period_start,
        )
        .first()
    )
    now = datetime.utcnow()
    if row:
        row.used_count = int(row.used_count) + amount
        row.updated_at = now
    else:
        db.add(
            FeatureUsage(
                user_id=user_id,
                feature_key=feature_key,
                period_type=period_type,
                period_start=period_start,
                used_count=amount,
                created_at=now,
                updated_at=now,
            )
        )
    if commit:
        db.commit()


def increment_many_usage(
    db: Session,
    user_id: int,
    increments: list[tuple[str, str]],
    timezone: str | None = None,
    amount: int = 1,
) -> None:
    """
    Атомарно увеличивает несколько usage-счётчиков пользователя.

    increments: список пар (feature_key, period_type), например:
    [
        ("daily_photo_recognition_limit", "daily"),
        ("monthly_photo_recognition_limit", "monthly"),
        ("daily_ai_requests_limit", "daily"),
    ]

    Все изменения коммитятся одним db.commit(). При ошибке — rollback.

    Будущий ИИ-чат должен использовать эту же функцию, например:
    increment_many_usage(
        db=db,
        user_id=user.id,
        increments=[
            ("daily_ai_chat_messages_limit", "daily"),
            ("daily_ai_requests_limit", "daily"),
        ],
        timezone=user.timezone,
    )
    """
    try:
        for feature_key, period_type in increments:
            increment_usage(
                db=db,
                user_id=user_id,
                feature_key=feature_key,
                period_type=period_type,
                amount=amount,
                timezone=timezone,
                commit=False,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise


def _limit_exceeded_message(limit_feature_key: str) -> str:
    return LIMIT_DENIED_MESSAGES.get(limit_feature_key, "Лимит исчерпан для вашего тарифа.")


def check_limit_or_raise(
    db: Session,
    user_id: int,
    enabled_feature_key: str,
    limit_feature_key: str,
    period_type: str,
    timezone: str | None = None,
) -> None:
    if not is_feature_enabled(db, user_id, enabled_feature_key, default=False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=LIMIT_DENIED_MESSAGES.get(enabled_feature_key, "Функция недоступна на вашем тарифе."),
        )

    limit = get_feature_limit(db, user_id, limit_feature_key, default=0)
    if limit == -1:
        return
    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_limit_exceeded_message(limit_feature_key),
        )

    used = get_usage_count(db, user_id, limit_feature_key, period_type, timezone)
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_limit_exceeded_message(limit_feature_key),
        )


def check_limit_only_or_raise(
    db: Session,
    user_id: int,
    limit_feature_key: str,
    period_type: str,
    timezone: str | None = None,
) -> None:
    """Проверка только числового лимита (без отдельного boolean feature)."""
    limit = get_feature_limit(db, user_id, limit_feature_key, default=0)
    if limit == -1:
        return
    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_limit_exceeded_message(limit_feature_key),
        )
    used = get_usage_count(db, user_id, limit_feature_key, period_type, timezone)
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=_limit_exceeded_message(limit_feature_key),
        )


def check_daily_ai_request_limit(db: Session, user: User) -> None:
    check_limit_only_or_raise(
        db=db,
        user_id=user.id,
        limit_feature_key="daily_ai_requests_limit",
        period_type="daily",
        timezone=user.timezone,
    )


def check_feature_enabled_or_raise(db: Session, user_id: int, feature_key: str) -> None:
    if not is_feature_enabled(db, user_id, feature_key, default=False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=LIMIT_DENIED_MESSAGES.get(feature_key, "Функция недоступна на вашем тарифе."),
        )


def check_photo_recognition_limits(db: Session, user: User) -> None:
    tz = user.timezone
    check_feature_enabled_or_raise(db, user.id, "food_photo_recognition_enabled")
    check_limit_only_or_raise(
        db=db,
        user_id=user.id,
        limit_feature_key="daily_photo_recognition_limit",
        period_type="daily",
        timezone=tz,
    )
    check_limit_only_or_raise(
        db=db,
        user_id=user.id,
        limit_feature_key="monthly_photo_recognition_limit",
        period_type="monthly",
        timezone=tz,
    )
    check_daily_ai_request_limit(db, user)


def record_photo_recognition_usage(db: Session, user: User) -> None:
    increment_many_usage(
        db=db,
        user_id=user.id,
        increments=[
            ("daily_photo_recognition_limit", "daily"),
            ("monthly_photo_recognition_limit", "monthly"),
            ("daily_ai_requests_limit", "daily"),
        ],
        timezone=user.timezone,
    )


def check_label_analysis_limits(db: Session, user: User) -> None:
    check_feature_enabled_or_raise(db, user.id, "label_analysis_enabled")
    check_limit_only_or_raise(
        db=db,
        user_id=user.id,
        limit_feature_key="monthly_label_analysis_limit",
        period_type="monthly",
        timezone=user.timezone,
    )
    check_daily_ai_request_limit(db, user)


def record_label_analysis_usage(db: Session, user: User) -> None:
    increment_many_usage(
        db=db,
        user_id=user.id,
        increments=[
            ("monthly_label_analysis_limit", "monthly"),
            ("daily_ai_requests_limit", "daily"),
        ],
        timezone=user.timezone,
    )


def check_text_ai_limits(db: Session, user: User) -> None:
    """Текстовый анализ без фото — только общий дневной лимит ИИ."""
    check_daily_ai_request_limit(db, user)


def record_text_ai_usage(db: Session, user: User) -> None:
    increment_many_usage(
        db=db,
        user_id=user.id,
        increments=[
            ("daily_ai_requests_limit", "daily"),
        ],
        timezone=user.timezone,
    )
