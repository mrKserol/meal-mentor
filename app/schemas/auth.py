from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.additives import DayNutritionTotals


class AuthRegisterRequest(BaseModel):
    telegram_username: str | None = None
    first_name: str | None = None
    sex: str | None = None
    birth_date: date | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    goal: str | None = None
    activity_level: str | None = None
    target_weight_kg: float | None = None
    timezone: str | None = None
    email: EmailStr
    password: str


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class AuthLogoutRequest(BaseModel):
    refresh_token: str


class AuthTokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_in: int


class AuthTelegramRequest(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str
    timezone: str | None = None


class AuthTelegramCallbackRequest(BaseModel):
    code: str
    state: str
    code_verifier: str
    redirect_uri: str
    timezone: str | None = None


class AuthYandexCallbackRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str
    timezone: str | None = None


class NutritionTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bmr_kcal: int
    tdee_kcal: int
    target_calories: int
    target_fiber_g: float
    target_protein_g: int
    target_fat_g: int
    target_carbs_g: int
    formula_name: str
    goal: str | None = None
    activity_level: str | None = None
    weight_kg: float | None = None
    target_weight_kg: float | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr | None
    username: str | None
    first_name: str | None
    sex: str | None
    birth_date: date | None
    height_cm: int | None
    weight_kg: float | None
    goal: str | None
    activity_level: str | None
    target_weight_kg: float | None
    timezone: str | None
    language: str
    telegram_id: int | None
    role: str
    status: str
    subscription_status: str
    created_at: datetime
    updated_at: datetime | None
    profile_completed: bool
    nutrition_target: NutritionTargetResponse | None = None
    allergens: list[str] = Field(default_factory=list)


class MyNutritionTargetResponse(BaseModel):
    nutrition_target: NutritionTargetResponse | None = None


class WeightMeasurementCreateRequest(BaseModel):
    weight_kg: float = Field(gt=0, le=500)
    waist_cm: float | None = Field(default=None, gt=0, le=300)
    body_fat_percent: float | None = Field(default=None, ge=0, le=80)
    notes: str | None = Field(default=None, max_length=1000)


class WeightMeasurementResponse(BaseModel):
    id: int
    measured_at: datetime
    weight_kg: float
    waist_cm: float | None = None
    body_fat_percent: float | None = None
    notes: str | None = None
    nutrition_target: NutritionTargetResponse | None = None


class WeightMeasurementPoint(BaseModel):
    id: int
    measured_at: datetime
    weight_kg: float
    waist_cm: float | None = None
    body_fat_percent: float | None = None
    notes: str | None = None


class WeightMeasurementsResponse(BaseModel):
    period: str
    items: list[WeightMeasurementPoint]


class OAuthAuthResponse(AuthTokenPair):
    user: UserMeResponse
    is_new_user: bool
    profile_completed: bool


class TelegramAuthResponse(OAuthAuthResponse):
    pass


class LabelAnalysisResponse(BaseModel):
    """Ответ анализа этикетки (текст как в Telegram check_ingredients)."""

    text: str


class WebMealSaveRequest(BaseModel):
    """Сохранение приёма пищи для текущего веб-пользователя (JWT), без telegram_id."""

    ingredients: dict[str, Any]
    source_type: str = "photo"
    telegram_file_id: str | None = None
    prediction: str | None = None
    prediction_translated: str | None = None
    prediction_language: str | None = None
    user_text: str | None = None
    image_base64: str | None = None
    meal_photo_large: str | None = None
    meal_photo_thumb: str | None = None
    meal_local_date: date | None = Field(
        default=None,
        description="Deprecated: prefer meal_local_datetime. Uses that day at current local time.",
    )
    meal_local_datetime: str | None = Field(
        default=None,
        description="Local wall time in user TZ: YYYY-MM-DDTHH:mm (not after end of tomorrow).",
    )


class WebMealSaveResponse(BaseModel):
    status: str


class WebMealUpdateRequest(BaseModel):
    """Обновление состава существующего приёма (JWT)."""

    ingredients: dict[str, Any] | None = None
    prediction: str | None = None
    prediction_translated: str | None = None
    prediction_language: str | None = None
    shift_days: int | None = None


class FoodNameResolveRequest(BaseModel):
    name: str
    grams: int | None = None
    state: str | None = None


class FoodNameResolveResponse(BaseModel):
    status: str
    input_name: str
    canonical_name: str | None = None
    display_name: str | None = None
    language: str | None = None
    default_state: str | None = None
    category: str | None = None
    source: str | None = None
    confidence: float | None = None
    error: str = ""


class WebMealUpdateResponse(BaseModel):
    status: str


class WebMealDayItemLine(BaseModel):
    id: int
    item_name: str | None = None
    name_translated: str | None = None
    name_language: str | None = None
    display_name: str | None = None
    ingredient_state: str | None = None
    estimated_weight_g: int | None = None
    calories: int | None = None
    protein_g: int | None = None
    fat_g: int | None = None
    carbs_g: int | None = None
    fiber_g: float | None = None


class WebMealDayRow(BaseModel):
    id: int
    prediction: str | None = None
    prediction_translated: str | None = None
    prediction_language: str | None = None
    display_prediction: str | None = None
    user_text: str | None = None
    time_local: str
    date_local: str = ""
    meal_type: str | None = None
    meal_type_label: str
    composition: str
    calories: int
    protein_g: int = 0
    fat_g: int = 0
    carbs_g: int = 0
    fiber_g: float = 0.0
    sugar_g: int = 0
    sodium_mg: int = 0
    saturated_fat_g: float = 0.0
    water_g: float = 0.0
    meal_photo_thumb: str | None = None
    meal_photo_large: str | None = None
    meal_photo_thumb_url: str | None = None
    meal_photo_large_url: str | None = None
    items: list[WebMealDayItemLine] = Field(default_factory=list)


class WebMealsDayResponse(BaseModel):
    date: date
    items: list[WebMealDayRow]
    additive_totals: DayNutritionTotals | None = None


class ProfilePatchRequest(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    sex: str | None = None
    birth_date: date | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    goal: str | None = None
    activity_level: str | None = None
    target_weight_kg: float | None = None
    allergens: list[str] | None = None
    language: str | None = None
