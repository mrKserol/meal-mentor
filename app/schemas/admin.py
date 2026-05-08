from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminUserListItem(BaseModel):
    id: int
    email: str | None = None
    telegram_id: int | None = None
    username: str | None = None
    first_name: str | None = None
    role: str
    status: str
    subscription_status: str
    created_at: datetime
    updated_at: datetime | None = None
    active_subscription_ends_at: datetime | None = None


class AdminUserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, pattern="^(user|admin)$")
    status: str | None = Field(default=None, pattern="^(active|blocked)$")
    subscription_status: str | None = None


class AdminPlanFeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    feature_key: str
    feature_name: str
    value_type: str
    value_bool: bool | None = None
    value_int: int | None = None
    value_text: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AdminPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    price_amount: int
    currency: str
    period_days: int
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime | None = None
    features: list[AdminPlanFeatureResponse] = Field(default_factory=list)


class AdminPlanCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price_amount: int = Field(default=0, ge=0)
    currency: str = Field(default="RUB", min_length=1, max_length=8)
    period_days: int = Field(default=30, gt=0)
    is_active: bool = True
    sort_order: int = 100


class AdminPlanUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price_amount: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=1, max_length=8)
    period_days: int | None = Field(default=None, gt=0)
    is_active: bool | None = None
    sort_order: int | None = None


class AdminPlanFeatureUpsertRequest(BaseModel):
    feature_key: str = Field(min_length=1, max_length=64)
    feature_name: str = Field(min_length=1, max_length=255)
    value_type: str = Field(default="limit", pattern="^(boolean|limit|text)$")
    value_bool: bool | None = None
    value_int: int | None = None
    value_text: str | None = None


class AdminSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_email: str | None = None
    user_name: str | None = None
    plan: str
    plan_id: int | None = None
    plan_name: str | None = None
    status: str
    provider: str | None = None
    payment_status: str | None = None
    started_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    activated_by_admin_id: int | None = None


class AdminGrantSubscriptionRequest(BaseModel):
    plan_id: int
    days: int | None = Field(default=None, gt=0)


class AdminUserFeatureOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    feature_key: str
    value_type: str
    value_bool: bool | None = None
    value_int: int | None = None
    value_text: str | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class AdminUserFeatureOverrideUpsertRequest(BaseModel):
    feature_key: str = Field(min_length=1, max_length=64)
    value_type: str = Field(default="limit", pattern="^(boolean|limit|text)$")
    value_bool: bool | None = None
    value_int: int | None = None
    value_text: str | None = None
    reason: str | None = None


class AdminUserDetail(AdminUserListItem):
    active_subscription: AdminSubscriptionResponse | None = None
    subscriptions: list[AdminSubscriptionResponse] = Field(default_factory=list)
    feature_overrides: list[AdminUserFeatureOverrideResponse] = Field(default_factory=list)
