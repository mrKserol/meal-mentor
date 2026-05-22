from datetime import datetime

from pydantic import BaseModel


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
