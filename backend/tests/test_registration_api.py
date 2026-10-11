
import pytest
from fastapi.testclient import TestClient

from app.auth.utils import hash_password, verify_password
from app.database.database import get_db
from app.main import app
from app.models.user import User


class FakeResult:
    def __init__(self, user):
        self.user = user

    def scalar_one_or_none(self):
        return self.user


class FakeDB:
    def __init__(self, existing_user=None):
        self.existing_user = existing_user
        self.added_user = None
        self.committed = False
        self.refreshed = False

    async def execute(self, query):
        return FakeResult(self.existing_user)

    def add(self, instance):
        self.added_user = instance

    async def commit(self):
        self.committed = True

    async def refresh(self, instance):
        instance.id = 10
        self.refreshed = True


@pytest.fixture
def registration_client():
    state = {"db": None}

    async def override_get_db():
        db = FakeDB()
        state["db"] = db
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client, state

    client.close()
    app.dependency_overrides.clear()


def test_registration_creates_user_with_hashed_password(registration_client):
    client, state = registration_client

    response = client.post("/auth/register", json={
        "full_name": "Test Student",
        "email": "12345678@uap-bd.edu",
        "password": "StrongPass123!",
        "confirm_password": "StrongPass123!",
    })

    assert response.status_code == 201
    assert response.json()["email"] == "12345678@uap-bd.edu"
    assert response.json()["full_name"] == "Test Student"
    assert "password" not in response.json()
    assert "password_hash" not in response.json()

    db = state["db"]
    assert db.committed
    assert db.refreshed
    assert db.added_user is not None
    assert db.added_user.role_id == 1
    assert db.added_user.is_active is True
    assert db.added_user.password_hash != "StrongPass123!"
    assert verify_password("StrongPass123!", db.added_user.password_hash)


def test_registration_rejects_duplicate_email(registration_client):
    client, state = registration_client

    existing_user = User(
        id=1,
        name="Existing Student",
        email="12345678@uap-bd.edu",
        password_hash=hash_password("ExistingPass123!"),
        role_id=1,
        is_active=True,
    )

    async def override_get_db():
        db = FakeDB(existing_user=existing_user)
        state["db"] = db
        yield db

    app.dependency_overrides[get_db] = override_get_db

    response = client.post("/auth/register", json={
        "full_name": "Another Student",
        "email": "12345678@uap-bd.edu",
        "password": "StrongPass123!",
        "confirm_password": "StrongPass123!",
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"
    assert state["db"].added_user is None
    assert not state["db"].committed
