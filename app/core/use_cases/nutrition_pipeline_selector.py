from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy.orm import Session

from app.core.config import NUTRITION_PIPELINE_GLOBAL_SETTING_KEY
from app.db.models import AppSetting, User


class NutritionPipelineVersion(StrEnum):
    GLOBAL = "global"
    V1_CSV = "v1_csv"
    V2_USDA = "v2_usda"


ALLOWED_USER_PIPELINES = {"global", "v1_csv", "v2_usda"}
ALLOWED_GLOBAL_PIPELINES = {"v1_csv", "v2_usda"}


def normalize_user_pipeline_version(value: str | None) -> str:
    if value in ALLOWED_USER_PIPELINES:
        return value
    return NutritionPipelineVersion.GLOBAL.value


def normalize_global_pipeline_version(value: str | None) -> str:
    if value in ALLOWED_GLOBAL_PIPELINES:
        return value
    return NutritionPipelineVersion.V1_CSV.value


def get_global_nutrition_pipeline(db: Session) -> str:
    """
    Read app_settings['nutrition_pipeline_global_version'].
    If not found or invalid, return v1_csv.
    """
    setting = db.query(AppSetting).filter(AppSetting.key == NUTRITION_PIPELINE_GLOBAL_SETTING_KEY).first()
    return normalize_global_pipeline_version(setting.value if setting else None)


def set_global_nutrition_pipeline(db: Session, value: str) -> str:
    """
    Validate value and upsert app_settings['nutrition_pipeline_global_version'].
    Return saved value.
    """
    normalized = normalize_global_pipeline_version(value)
    setting = db.query(AppSetting).filter(AppSetting.key == NUTRITION_PIPELINE_GLOBAL_SETTING_KEY).first()
    if setting is None:
        setting = AppSetting(
            key=NUTRITION_PIPELINE_GLOBAL_SETTING_KEY,
            value=normalized,
            updated_at=datetime.utcnow(),
        )
        db.add(setting)
    else:
        setting.value = normalized
        setting.updated_at = datetime.utcnow()
    db.commit()
    return normalized


def resolve_user_nutrition_pipeline(db: Session, user: User | None) -> str:
    """
    If user.nutrition_pipeline_version is v1_csv or v2_usda, return it.
    If user setting is global/empty/invalid, return global setting.
    Final fallback is v1_csv.
    """
    user_value = normalize_user_pipeline_version(
        getattr(user, "nutrition_pipeline_version", None) if user is not None else None
    )
    if user_value in (NutritionPipelineVersion.V1_CSV.value, NutritionPipelineVersion.V2_USDA.value):
        return user_value
    return normalize_global_pipeline_version(get_global_nutrition_pipeline(db))
