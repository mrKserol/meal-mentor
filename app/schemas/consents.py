from datetime import datetime

from pydantic import BaseModel


class ConsentStatusResponse(BaseModel):
    required: bool
    accepted: bool
    consent_type: str
    current_version: str
    accepted_at: datetime | None = None


class ConsentAcceptRequest(BaseModel):
    consent_type: str
    consent_version: str


class ConsentAcceptResponse(BaseModel):
    accepted: bool
    consent_type: str
    consent_version: str
    accepted_at: datetime
