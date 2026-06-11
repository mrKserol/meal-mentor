from datetime import datetime

from pydantic import BaseModel, Field


class AiChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
        orm_mode = True


class AiChatThreadResponse(BaseModel):
    id: int
    status: str
    title: str | None = None
    last_message_at: datetime | None = None
    messages: list[AiChatMessageResponse] = []

    class Config:
        from_attributes = True
        orm_mode = True


class AiChatSendRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class AiChatSendResponse(BaseModel):
    thread_id: int
    user_message: AiChatMessageResponse
    assistant_message: AiChatMessageResponse


class AiChatBootstrapResponse(BaseModel):
    thread_id: int | None = None
    disclaimer_required: bool
    disclaimer_version: str
    messages: list[AiChatMessageResponse] = []
