import hashlib
from datetime import datetime, timedelta
import importlib

from fastapi.testclient import TestClient

from app.auth.utils import verify_password
from app.database.database import get_db
from app.main import app
from app.models.user import User

auth_router = importlib.import_module("app.auth.router")


class FakeResult:
    def __init__(self, user):
        self.user = user

    def scalar_one_or_none(self):
        return self.user


class FakeDB:
    def __init__(self, user):
        self.user = user

    async def execute(self, statement):
        query = str(statement.whereclause)
        params = statement.compile().params

        if "password_reset_token_hash" in query:
            token_hash = next(iter(params.values()), None)
            found = (
                self.user
                if self.user
                and self.user.password_reset_token_hash == token_hash
                else None
            )
        else:
            email = next(iter(params.values()), None)
            found = (
                self.user
                if self.user and self.user.email == email
                else None
            )

        return FakeResult(found)

    async def commit(self):
        pass


def make_user():
    return User(
        id=1,
        name="Test Student",
        email="12345678@uap-bd.edu",
        password_hash="old-hash",
        role_id=1,
        is_active=True,
    )


def make_client(user):
    async def override_get_db():
        yield FakeDB(user)

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_forgot_password_creates_hashed_token_and_schedules_email(monkeypatch):
    user = make_user()
    sent = []

    monkeypatch.setattr(
        auth_router,
        "send_password_reset_email",
        lambda email, token: sent.append((email, token)),
    )
    client = make_client(user)

    try:
        response = client.post(
            "/auth/forgot-password",
            json={"email": user.email},
        )

        assert response.status_code == 200
        assert user.password_reset_token_hash
        assert len(user.password_reset_token_hash) == 64
        assert user.password_reset_expires_at > datetime.utcnow()
        assert len(sent) == 1
        assert sent[0][0] == user.email
        assert hashlib.sha256(sent[0][1].encode()).hexdigest() == (
            user.password_reset_token_hash
        )
        assert sent[0][1] != user.password_reset_token_hash
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_reset_password_updates_password_and_consumes_token():
    user = make_user()
    raw_token = "test-reset-token"
    user.password_reset_token_hash = hashlib.sha256(
        raw_token.encode()
    ).hexdigest()
    user.password_reset_expires_at = datetime.utcnow() + timedelta(minutes=30)

    client = make_client(user)

    try:
        response = client.post(
            "/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewStrongPass123!",
            },
        )

        assert response.status_code == 200
        assert verify_password("NewStrongPass123!", user.password_hash)
        assert user.password_reset_token_hash is None
        assert user.password_reset_expires_at is None
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_reset_password_rejects_invalid_token():
    user = make_user()
    user.password_reset_token_hash = hashlib.sha256(
        b"another-token"
    ).hexdigest()
    user.password_reset_expires_at = datetime.utcnow() + timedelta(minutes=30)

    client = make_client(user)

    try:
        response = client.post(
            "/auth/reset-password",
            json={
                "token": "wrong-token",
                "new_password": "NewStrongPass123!",
            },
        )

        assert response.status_code == 400
        assert user.password_hash == "old-hash"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_reset_password_rejects_expired_token():
    user = make_user()
    raw_token = "expired-reset-token"
    user.password_reset_token_hash = hashlib.sha256(
        raw_token.encode()
    ).hexdigest()
    user.password_reset_expires_at = datetime.utcnow() - timedelta(minutes=1)

    client = make_client(user)

    try:
        response = client.post(
            "/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "NewStrongPass123!",
            },
        )

        assert response.status_code == 400
        assert user.password_hash == "old-hash"
    finally:
        client.close()
        app.dependency_overrides.clear()

