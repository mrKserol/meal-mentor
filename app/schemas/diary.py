from datetime import date, datetime

from pydantic import BaseModel, Field


class DiaryRecentMeal(BaseModel):
    id: int
    title: str
    meal_type: str | None = None
    meal_type_label: str
    time_local: str
    calories: int
    protein_g: int = 0
    fat_g: int = 0
    carbs_g: int = 0
    fiber_g: int = 0
    recorded_at: datetime
    prediction: str | None = None
    user_text: str | None = None
    composition: str = ""
    meal_photo_large: str | None = None
    meal_photo_thumb: str | None = None
    meal_photo_large_url: str | None = None
    meal_photo_thumb_url: str | None = None


class DiaryWeekDay(BaseModel):
    date: date
    weekday_short: str
    calories: int
    bar_percent: int = Field(ge=0, le=100, description="Высота столбца 0–100 относительно максимума за неделю")


class DiaryWeekBlock(BaseModel):
    days: list[DiaryWeekDay]
    avg_calories: float
    avg_protein_g: float
    avg_fat_g: float
    avg_carbs_g: float
    days_with_data: int = Field(
        ...,
        description="Дней с ненулевыми калориями; средние делятся на это число (минимум 1)",
    )


class DiaryTodayTotals(BaseModel):
    calories: int
    protein_g: int
    fat_g: int
    carbs_g: int


class DiaryWeightCard(BaseModel):
    weight_kg: float | None = None
    delta_week_kg: float | None = Field(
        default=None,
        description="Изменение за текущую календарную неделю (последнее − первое взвешивание), кг",
    )


class DiaryPeriodDay(BaseModel):
    date: date
    label: str
    calories: int
    bar_percent: int = Field(ge=0, le=100, description="Высота столбца 0–100 относительно максимума за период")


class DiaryPeriodBlock(BaseModel):
    days: list[DiaryPeriodDay]
    avg_calories: float
    avg_protein_g: float
    avg_fat_g: float
    avg_carbs_g: float
    days_with_data: int = Field(
        ...,
        description="Дней с ненулевыми калориями; средние делятся на это число (минимум 1)",
    )


class DiarySnapshotResponse(BaseModel):
    today_meals: list[DiaryRecentMeal]
    week: DiaryWeekBlock
    month: DiaryPeriodBlock
    today: DiaryTodayTotals
    weight: DiaryWeightCard
