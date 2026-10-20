from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.event import Event
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

    def scalars(self):
        return self

    def all(self):
        return self.value


class FakeDB:
    def __init__(self, state):
        self.state = state
        self.committed = False
        self.queries = []

    async def execute(self, query):
        self.queries.append(str(query))
        if "FROM events" in str(query):
            return FakeResult(self.state.get("events", []))
        return FakeResult(self.state["profile"])

    def add(self, instance):
        if isinstance(instance, OrganizerProfile):
            instance.user = self.state["user"]
            self.state["profile"] = instance

    async def commit(self):
        self.committed = True


def make_user(role_name="organizer", user_id=1):
    user = User(
        id=user_id,
        name="Test Organizer",
        email=f"{user_id}234567@uap-bd.edu",
        password_hash="test-hash",
        role_id=2 if role_name == "organizer" else 1,
        is_active=True,
    )
    user.role = Role(id=user.role_id, name=role_name)
    return user


@pytest.fixture
def setup_api():
    user = make_user()
    state = {"user": user, "profile": None, "events": []}
    db = FakeDB(state)

    async def override_get_db():
        yield db

    async def override_get_current_user():
        return state["user"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client, state, db

    client.close()
    app.dependency_overrides.clear()


def make_event(event_id, organizer_id=1, status="published"):
    return SimpleNamespace(
        id=event_id,
        organizer_id=organizer_id,
        title=f"Event {event_id}",
        description="Test event",
        category="Academic",
        event_date=datetime(2026, 11, 1).date(),
        start_time=datetime.strptime("10:00", "%H:%M").time(),
        end_time=datetime.strptime("11:00", "%H:%M").time(),
        mode="Offline",
        venue="UAP",
        capacity=100,
        registration_deadline=datetime(2026, 10, 30),
        status=status,
    )


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


def test_organizer_profile_includes_events(setup_api):
    client, state, _ = setup_api
    user = state["user"]
    profile = OrganizerProfile(user_id=user.id)
    profile.user = user
    state["profile"] = profile
    state["events"] = [
        make_event(10, organizer_id=user.id, status="published"),
        make_event(11, organizer_id=user.id, status="completed"),
        make_event(12, organizer_id=user.id, status="cancelled"),
    ]

    response = client.get(f"/organizer-profiles/{user.id}")

    assert response.status_code == 200
    data = response.json()
    assert [event["id"] for event in data["events"]] == [10, 11, 12]
    assert {event["status"] for event in data["events"]} == {
        "published",
        "completed",
        "cancelled",
    }


def test_organizer_profile_returns_empty_events_list(setup_api):
    client, state, _ = setup_api
    profile = OrganizerProfile(user_id=state["user"].id)
    profile.user = state["user"]
    state["profile"] = profile
    state["events"] = []

    response = client.get(f"/organizer-profiles/{state['user'].id}")

    assert response.status_code == 200
    assert response.json()["events"] == []


def test_missing_organizer_profile_returns_404(setup_api):
    client, _, _ = setup_api

    response = client.get("/organizer-profiles/999")

    assert response.status_code == 404
