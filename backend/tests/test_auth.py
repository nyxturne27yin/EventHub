from pydantic import ValidationError
import pytest

from app.auth.schemas import RegisterRequest


def test_valid_registration_data():
    data = RegisterRequest(
        full_name="Test Student",
        email="12345678@uap-bd.edu",
        password="StrongPass123!",
        confirm_password="StrongPass123!",
    )

    assert data.full_name == "Test Student"
    assert str(data.email) == "12345678@uap-bd.edu"
    assert data.password == "StrongPass123!"


def test_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="Test Student",
            email="invalid-email",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        )


def test_non_uap_email_is_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="Test Student",
            email="student@gmail.com",
            password="StrongPass123!",
            confirm_password="StrongPass123!",
        )


def test_password_must_be_at_least_8_characters():
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="Test Student",
            email="12345678@uap-bd.edu",
            password="Abc123!",
            confirm_password="Abc123!",
        )


def test_password_does_not_require_uppercase():
    data = RegisterRequest(
        full_name="Test Student",
        email="12345678@uap-bd.edu",
        password="strongpass123!",
        confirm_password="strongpass123!",
    )
    assert data.password == "strongpass123!"


def test_password_does_not_require_lowercase():
    data = RegisterRequest(
        full_name="Test Student",
        email="12345678@uap-bd.edu",
        password="STRONGPASS123!",
        confirm_password="STRONGPASS123!",
    )
    assert data.password == "STRONGPASS123!"


def test_password_requires_number():
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="Test Student",
            email="12345678@uap-bd.edu",
            password="StrongPassword!",
            confirm_password="StrongPassword!",
        )


def test_password_requires_special_character():
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name="Test Student",
            email="12345678@uap-bd.edu",
            password="StrongPass123",
            confirm_password="StrongPass123",
        )