
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.organizer_profile import OrganizerProfile
from app.models.role import Role
from app.models.user import User


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        assert self.value is not None
        return self.value


class FakeDB:
    def __init__(self, state):
        self.state = state
        self.committed = False

    async def execute(self, query):
        return FakeResult(self.state["profile"])

    def add(self, instance):
        if isinstance(instance, OrganizerProfile):
            instance.user = self.state["user"]
            self.state["profile"] = instance

    async def commit(self):
        self.committed = True


def make_user(role_name="organizer"):
    user = User(
        id=1,
        name="Test Organizer",
        email="1234567@uap-bd.edu",
        password_hash="test-hash",
        role_id=2 if role_name == "organizer" else 1,
        is_active=True,
    )
    user.role = Role(id=user.role_id, name=role_name)
    return user


@pytest.fixture
def setup_api():
    user = make_user()
    state = {"user": user, "profile": None}
    db = FakeDB(state)

    async def override_get_db():
        yield db

    async def override_get_current_user():
        return state["user"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    client = TestClient(app)
    yield client, state, db

    client.close()
    app.dependency_overrides.clear()


def test_organizer_can_view_empty_profile(setup_api):
    client, state, _ = setup_api

    response = client.get("/organizer-profiles/me")

    assert response.status_code == 200
    assert response.json()["name"] == "Test Organizer"
    assert response.json()["organization_name"] is None
    assert state["profile"] is None


def test_organizer_can_create_profile(setup_api):
    client, state, db = setup_api

    response = client.put(
        "/organizer-profiles/me",
        json={
            "organization_name": "CSE Club",
            "department": "CSE",
            "bio": "University student organization",
            "contact_phone": "01700000000",
        },
    )

    assert response.status_code == 200
    assert response.json()["organization_name"] == "CSE Club"
    assert response.json()["department"] == "CSE"
    assert state["profile"].organization_name == "CSE Club"
    assert db.committed is True


def test_student_cannot_update_organizer_profile(setup_api):
    client, state, db = setup_api
    state["user"] = make_user(role_name="student")

    response = client.put(
        "/organizer-profiles/me",
        json={"organization_name": "CSE Club"},
    )

    assert response.status_code == 403
    assert state["profile"] is None
    assert db.committed is False


def test_unknown_profile_field_is_rejected(setup_api):
    client, state, db = setup_api

    response = client.put(
        "/organizer-profiles/me",
        json={
            "organization_name": "CSE Club",
            "unknown_field": "not allowed",
        },
    )

    assert response.status_code == 422
    assert state["profile"] is None
    assert db.committed is False


def test_profile_fields_are_trimmed(setup_api):
    client, state, _ = setup_api

    response = client.put(
        "/organizer-profiles/me",
        json={"organization_name": "  CSE Club  "},
    )

    assert response.status_code == 200
    assert response.json()["organization_name"] == "CSE Club"
    assert state["profile"].updated_at is not None
