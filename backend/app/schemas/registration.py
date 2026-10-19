from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RegistrationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegistrationStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["Registered", "Cancelled"]


class ParticipantItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    participant_id: int
    status: Literal["Registered", "Cancelled"]
    created_at: datetime
    participant_name: str
    participant_email: str
