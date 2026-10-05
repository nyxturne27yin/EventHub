from pydantic import ValidationError
import pytest

from app.auth.schemas import RegisterRequest


def test_valid_registration_data():
    data = RegisterRequest(
        name="Test Student",
        email="student@uap-bd.edu",
        password="StrongPass123!",
    )

    assert data.name == "Test Student"
    assert str(data.email) == "student@uap-bd.edu"
    assert data.password == "StrongPass123!"


def test_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="invalid-email",
            password="StrongPass123!",
        )


def test_non_uap_email_is_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="student@gmail.com",
            password="StrongPass123!",
        )


def test_password_must_be_at_least_8_characters():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="student@uap-bd.edu",
            password="Abc123!",
        )


def test_password_requires_uppercase():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="student@uap-bd.edu",
            password="strongpass123!",
        )


def test_password_requires_lowercase():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="student@uap-bd.edu",
            password="STRONGPASS123!",
        )


def test_password_requires_number():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="student@uap-bd.edu",
            password="StrongPassword!",
        )


def test_password_requires_special_character():
    with pytest.raises(ValidationError):
        RegisterRequest(
            name="Test Student",
            email="student@uap-bd.edu",
            password="StrongPass123",
        )