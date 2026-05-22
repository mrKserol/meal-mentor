from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.db.nutrition_columns import MEAL_ITEM_NUTRITION_KEYS
from app.services.user_timezone import absolute_public_url, resolve_tz, utc_naive_to_local


class NutrientFieldResponse(BaseModel):
    key: str
    label: str
    unit: str


class AdditiveAnalyzeRequest(BaseModel):
    image_base64: str


class AdditiveAnalyzeResponse(BaseModel):
    status: str
    serving_label: str | None = None
    serving_size_g: float | None = None
    nutrients: dict[str, float] = Field(default_factory=dict)
    ignored: list[dict[str, str | None]] = Field(default_factory=list)
    confidence: float | None = None
    error: str | None = None


class AdditiveCreateRequest(BaseModel):
    additive_name: str
    serving_label: str | None = None
    serving_size_g: float | None = None
    image_base64: str | None = None
    nutrients: dict[str, float] = Field(default_factory=dict)


class AdditiveUpdateRequest(BaseModel):
    additive_name: str | None = None
    serving_label: str | None = None
    serving_size_g: float | None = None
    image_base64: str | None = None
    nutrients: dict[str, float] | None = None


def nutrients_dict_from_row(row: object) -> dict[str, float]:
    out: dict[str, float] = {}
    for key in MEAL_ITEM_NUTRITION_KEYS:
        val = getattr(row, key, None)
        if val is not None and val != 0:
            out[key] = float(val)
    return out


class AdditiveResponse(BaseModel):
    id: int
    additive_name: str
    photo_large: str | None = None
    photo_thumb: str | None = None
    photo_large_url: str | None = None
    photo_thumb_url: str | None = None
    serving_label: str | None = None
    serving_size_g: float | None = None
    nutrients: dict[str, float] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def from_orm_row(cls, row: object) -> "AdditiveResponse":
        return cls(
            id=row.id,
            additive_name=row.additive_name,
            photo_large=row.photo_large,
            photo_thumb=row.photo_thumb,
            photo_large_url=absolute_public_url(row.photo_large),
            photo_thumb_url=absolute_public_url(row.photo_thumb),
            serving_label=row.serving_label,
            serving_size_g=row.serving_size_g,
            nutrients=nutrients_dict_from_row(row),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class AdditiveListResponse(BaseModel):
    items: list[AdditiveResponse]


class AdditiveIntakeCreateRequest(BaseModel):
    additive_id: int
    servings_count: float
    intake_local_date: date | None = None


class WaterIntakeCreateRequest(BaseModel):
    amount_ml: float = 100
    intake_local_date: date | None = None


class AdditiveIntakeResponse(BaseModel):
    id: int
    additive_id: int | None = None
    additive_name_snapshot: str
    servings_count: float
    intake_datetime: datetime
    time_local: str
    nutrients: dict[str, float] = Field(default_factory=dict)
    water_g: float | None = None

    @classmethod
    def from_orm_row(cls, row: object, user: object) -> "AdditiveIntakeResponse":
        tz = resolve_tz(user)
        raw = row.intake_datetime
        naive = raw.replace(tzinfo=None) if raw.tzinfo else raw
        local = utc_naive_to_local(naive, tz)
        water = getattr(row, "water_g", None)
        return cls(
            id=row.id,
            additive_id=row.additive_id,
            additive_name_snapshot=row.additive_name_snapshot,
            servings_count=row.servings_count,
            intake_datetime=naive,
            time_local=local.strftime("%H:%M"),
            nutrients=nutrients_dict_from_row(row),
            water_g=float(water) if water is not None else None,
        )


class AdditiveIntakeListResponse(BaseModel):
    date: date
    items: list[AdditiveIntakeResponse]


class StatusResponse(BaseModel):
    status: str


class DayNutritionTotals(BaseModel):
    calories: float = 0
    protein_g: float = 0
    fat_g: float = 0
    carbs_g: float = 0
    fiber_g: float = 0
    sugar_g: float = 0
    sodium_mg: float = 0
    saturated_fat_g: float = 0
    water_g: float = 0
