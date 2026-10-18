from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrganizerProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_name: str | None = Field(default=None, max_length=150)
    department: str | None = Field(default=None, max_length=150)
    bio: str | None = Field(default=None, max_length=2000)
    contact_phone: str | None = Field(default=None, max_length=30)

    @field_validator(
        "organization_name",
        "department",
        "bio",
        "contact_phone",
    )
    @classmethod
    def clean_optional_fields(cls, value):
        if value is None:
            return None

        value = value.strip()
        return value or None