from datetime import date, datetime

from pydantic import BaseModel


class CuratorUserProfileResponse(BaseModel):
    id: int
    first_name: str | None = None
    birth_date: date | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    target_weight_kg: float | None = None
    activity_level: str | None = None


class CuratorUserListItem(BaseModel):
    id: int
    email: str | None = None
    username: str | None = None
    first_name: str | None = None
    role: str
    status: str
    subscription_status: str
    weight_kg: float | None = None
    created_at: datetime | None = None
