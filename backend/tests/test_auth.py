from pydantic import ValidationError
import pytest

from app.auth.schemas import RegisterRequest


def test_valid_registration_data():
    data = RegisterRequest(
        name="Test Student",
        email="student@example.com",
        password="StrongPass123",
    )

    assert data.name == "Test Student"
    assert str(data.email) == "student@example.com"


def test_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="invalid-email",
            password="StrongPass123",
        )


def test_password_must_be_at_least_8_characters():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="student@example.com",
            password="Abc123",
        )


def test_password_requires_uppercase():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="student@example.com",
            password="strongpass123",
        )


def test_password_requires_lowercase():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="student@example.com",
            password="STRONGPASS123",
        )


def test_password_requires_number():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="student@example.com",
            password="StrongPassword",
        )