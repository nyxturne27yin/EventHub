import re

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    field_validator,
    model_validator,
)


class RegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    confirm_password: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Full name is required")

        if len(value) > 100:
            raise ValueError("Full name must not exceed 100 characters")

        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        value = value.strip().lower()

        if len(value) > 255:
            raise ValueError("Email must not exceed 255 characters")

        # UAP student email format:
        # minimum 8 digit registration number + @uap-bd.edu
        if not re.fullmatch(r"[0-9]{8,}@uap-bd\.edu", value):
            raise ValueError(
                "Email must contain a valid registration number "
                "followed by @uap-bd.edu"
            )

        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(value) > 128:
            raise ValueError("Password must not exceed 128 characters")

        if not re.search(r"[A-Za-z]", value):
            raise ValueError("Password must contain at least one letter")

        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one number")

        if not re.search(r"[@$!%*?&]", value):
            raise ValueError(
                "Password must contain at least one special character"
            )

        return value

    @model_validator(mode="after")
    def validate_password_confirmation(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")

        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role_id: int

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str