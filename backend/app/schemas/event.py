from datetime import date, datetime, time
from typing import Literal
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)


class EventUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)

    event_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None

    mode: Literal["Online", "Offline"] | None = None
    venue: str | None = Field(default=None, max_length=255)
    meeting_link: str | None = Field(default=None, max_length=500)

    capacity: StrictInt | None = Field(default=None, gt=0)
    registration_deadline: datetime | None = None

    @field_validator("title", "category")
    @classmethod
    def strip_required_text(cls, value):
        if value is None:
            return value

        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")

        return value

    @field_validator("description", "venue", "meeting_link")
    @classmethod
    def strip_optional_text(cls, value):
        return value.strip() if value is not None else value

    @field_validator("meeting_link")
    @classmethod
    def validate_meeting_link(cls, value):
        if value is None or value == "":
            return value

        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(
                "Meeting link must be a valid HTTP or HTTPS URL"
            )

        return value

    @model_validator(mode="after")
    def validate_update_fields(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        non_nullable_fields = {
            "title",
            "description",
            "category",
            "event_date",
            "start_time",
            "end_time",
            "mode",
            "capacity",
            "registration_deadline",
        }

        for field in non_nullable_fields:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        return self