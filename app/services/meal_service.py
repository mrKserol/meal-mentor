"""
Thin facade over core use cases (keeps `app.services.meal_service` imports stable).
"""

from typing import Any

from sqlalchemy.orm import Session

from app.core.schemas import MealLogRequest
from app.core.use_cases.meal_analysis import (
    analyze_and_log_meal_legacy,
    analyze_meal_from_image_base64,
    analyze_meal_from_text,
    persist_meal_to_database,
)


def analyze_photo(image_base64: str) -> dict[str, Any]:
    """
    Vision analysis. Returns:
      status, ingredients, confidence, result (alias of ingredients), nutrition?, error
    """
    return analyze_meal_from_image_base64(image_base64).to_api_dict()


def analyze_text(user_text: str) -> dict[str, Any]:
    """Text-only analysis; same response shape as analyze_photo."""
    return analyze_meal_from_text(user_text).to_api_dict()


def save_meal_to_db(
    db: Session,
    telegram_id: int,
    username: str | None,
    ingredients: dict[str, Any],
    source_type: str,
    telegram_file_id: str | None = None,
    *,
    first_name: str | None = None,
) -> dict[str, Any]:
    """Persist Meal + MealItem + MealItemNutrition after user confirmation."""
    req = MealLogRequest(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        ingredients=ingredients,
        source_type=source_type,
        telegram_file_id=telegram_file_id,
    )
    return persist_meal_to_database(db, req).to_api_dict()


def log_meal(
    db: Session,
    telegram_id: int,
    username: str | None,
    image_base64: str,
    telegram_file_id: str | None = None,
    *,
    first_name: str | None = None,
) -> dict[str, Any]:
    """
    One-shot: analyze photo + save (legacy /meals/log). Prefer analyze + save for Telegram UX.
    """
    return analyze_and_log_meal_legacy(
        db,
        telegram_id=telegram_id,
        username=username,
        image_base64=image_base64,
        telegram_file_id=telegram_file_id,
        first_name=first_name,
    )
