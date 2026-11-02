from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.auth.utils import create_access_token, hash_password
from app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY
from app.database.database import get_db
from app.main import app
from app.models.user import User


class FakeResult:
    def __init__(self, user):
        self.user = user

    def scalar_one_or_none(self):
        return self.user


class FakeDB:
    def __init__(self, user=None):
        self.user = user

    async def execute(self, query):
        return FakeResult(self.user)

    async def commit(self):
        pass

    async def refresh(self, user):
        pass


def make_user():
    return User(
        id=1,
        name="Test Student",
        email="12345678@uap-bd.edu",
        password_hash=hash_password("StrongPass123!"),
        role_id=1,
        is_active=True,
    )


@pytest.fixture
def client():
    user = make_user()
    original_overrides = app.dependency_overrides.copy()

    async def override_get_db():
        yield FakeDB(user)

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)

    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def test_valid_login_returns_token(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "12345678@uap-bd.edu",
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["token_type"] == "bearer"


def test_wrong_password_is_rejected(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "12345678@uap-bd.edu",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_unknown_user_is_rejected():
    original_overrides = app.dependency_overrides.copy()

    async def override_get_db():
        yield FakeDB(None)

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)

    try:
        response = test_client.post(
            "/auth/login",
            json={
                "email": "87654321@uap-bd.edu",
                "password": "StrongPass123!",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"
    finally:
        test_client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def test_protected_route_without_token(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_protected_route_with_valid_token(client):
    token = create_access_token({"sub": "1"})

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_expired_token_is_rejected(client):
    expired_token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_malformed_token_subject_is_rejected(client):
    token = create_access_token({"sub": "not-a-user-id"})

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_inactive_user_cannot_login():
    original_overrides = app.dependency_overrides.copy()
    user = make_user()
    user.is_active = False

    async def override_get_db():
        yield FakeDB(user)

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)

    try:
        response = test_client.post(
            "/auth/login",
            json={
                "email": "12345678@uap-bd.edu",
                "password": "StrongPass123!",
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "User account is inactive"
    finally:
        test_client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def test_inactive_user_cannot_use_existing_token():
    original_overrides = app.dependency_overrides.copy()
    user = make_user()
    user.is_active = False

    async def override_get_db():
        yield FakeDB(user)

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    token = create_access_token({"sub": "1"})

    try:
        response = test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "User account is inactive"
    finally:
        test_client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def test_token_signed_with_wrong_secret_is_rejected(client):
    forged_token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "wrong-test-secret-for-security-testing",
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {forged_token}"},
    )

    assert response.status_code == 401


def test_token_without_subject_is_rejected(client):
    token = jwt.encode(
        {
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
