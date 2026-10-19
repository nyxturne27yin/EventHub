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


class EventCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=100)

    event_date: date
    start_time: time
    end_time: time

    mode: Literal["Online", "Offline"]
    venue: str | None = Field(default=None, max_length=255)
    meeting_link: str | None = Field(default=None, max_length=500)

    capacity: StrictInt = Field(gt=0)
    registration_deadline: datetime
    status: Literal["draft", "published"] = "draft"

    @field_validator("title", "description", "category")
    @classmethod
    def strip_required_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value

    @field_validator("venue", "meeting_link")
    @classmethod
    def strip_optional_text(cls, value):
        return value.strip() if value is not None else value

    @field_validator("meeting_link")
    @classmethod
    def validate_create_meeting_link(cls, value):
        if value is None or value == "":
            return value

        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(
                "Meeting link must be a valid HTTP or HTTPS URL"
            )

        return value

    @model_validator(mode="after")
    def validate_event(self):
        if self.event_date < date.today():
            raise ValueError("Event date cannot be in the past")

        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time")

        if self.registration_deadline.tzinfo is not None:
            raise ValueError(
                "Registration deadline must be local date and time"
            )

        event_start = datetime.combine(
            self.event_date,
            self.start_time,
        )

        if self.registration_deadline >= event_start:
            raise ValueError(
                "Registration deadline must be before the event starts"
            )

        if self.mode == "Offline" and not self.venue:
            raise ValueError("Venue is required for offline events")

        if self.mode == "Online" and not self.meeting_link:
            raise ValueError("Meeting link is required for online events")

        return self


class EventSearchItem(BaseModel):
    """Public event fields safe to expose on discovery and detail pages."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    category: str
    event_date: date
    start_time: time
    end_time: time
    mode: str
    venue: str | None = None
    capacity: int | None = None
    registered_count: int = 0
    registration_deadline: datetime | None = None
    status: str
