from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class AuthRegisterRequest(BaseModel):
    email: EmailStr
    username: str
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


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr | None
    username: str | None
    telegram_id: int | None
    subscription_status: str
    created_at: datetime
