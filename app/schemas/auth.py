from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr


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
    telegram_id: int | None
    subscription_status: str
    created_at: datetime
    updated_at: datetime | None
