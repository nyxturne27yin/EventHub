from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.event import Event
from app.models.registration import EventRegistration
from app.models.role import Role
from app.models.user import User


class FakeResult:
    def __init__(self, value=None, rows=None):
        self.value = value
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, event, registration, participant, registered_count=0):
        self.event = event
        self.registration = registration
        self.participant = participant
        self.registered_count = registered_count
        self.committed = False
        self.refreshed = False

    async def execute(self, query):
        entities = [
            description["entity"]
            for description in query.column_descriptions
        ]

        if entities[0] is Event:
            return FakeResult(self.event)

        if "count(" in str(query).lower():
            return FakeResult(self.registered_count)

        if len(entities) > 1 and entities[1] is User:
            return FakeResult(
                rows=[(self.registration, self.participant)]
                if self.registration and self.participant
                else []
            )

        return FakeResult(self.registration)

    async def commit(self):
        self.committed = True

    async def refresh(self, instance):
        self.refreshed = True


def make_user(user_id=1, role_name="organizer"):
    user = User(
        id=user_id,
        name=f"Test User {user_id}",
        email=f"{user_id}234567@uap-bd.edu",
        password_hash="test-hash",
        role_id=2 if role_name == "organizer" else 1,
        is_active=True,
    )
    user.role = Role(id=user.role_id, name=role_name)
    return user


def make_event(organizer_id=1):
    return Event(
        id=10,
        title="Test Event",
        description="Test description",
        category="Academic",
        event_date=date.today() + timedelta(days=10),
        start_time=time(10, 0),
        end_time=time(12, 0),
        mode="Offline",
        venue="UAP Campus",
        meeting_link=None,
        capacity=50,
        registration_deadline=datetime.now() + timedelta(days=5),
        status="published",
        organizer_id=organizer_id,
    )


@pytest.fixture
def registration_api():
    state = {
        "user": make_user(),
        "event": make_event(),
        "participant": make_user(2, "student"),
        "registration": None,
        "db": None,
    }

    state["registration"] = EventRegistration(
        id=20,
        event_id=10,
        participant_id=2,
        status="Registered",
        created_at=datetime.now(),
    )

    async def override_get_db():
        db = FakeDB(
            state["event"],
            state["registration"],
            state["participant"],
            state.get("registered_count", 0),
        )
        state["db"] = db
        yield db

    async def override_get_current_user():
        return state["user"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client, state

    client.close()
    app.dependency_overrides.clear()


def test_organizer_can_view_participant_status(registration_api):
    client, _ = registration_api

    response = client.get("/events/10/participants")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "Registered"
    assert response.json()[0]["participant_email"] == "2234567@uap-bd.edu"


def test_organizer_can_update_participant_status(registration_api):
    client, state = registration_api

    response = client.patch(
        "/events/10/registrations/20/status",
        json={"status": "Cancelled"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Cancelled"
    assert state["registration"].status == "Cancelled"
    assert state["db"].committed is True


def test_invalid_participant_status_is_rejected(registration_api):
    client, state = registration_api

    response = client.patch(
        "/events/10/registrations/20/status",
        json={"status": "Pending"},
    )

    assert response.status_code == 422
    assert state["registration"].status == "Registered"


def test_student_cannot_view_participants(registration_api):
    client, state = registration_api
    state["user"] = make_user(role_name="student")

    response = client.get("/events/10/participants")

    assert response.status_code == 403


def test_organizer_cannot_manage_another_organizers_participants(registration_api):
    client, state = registration_api
    state["event"].organizer_id = 99

    response = client.patch(
        "/events/10/registrations/20/status",
        json={"status": "Cancelled"},
    )

    assert response.status_code == 403
    assert state["registration"].status == "Registered"


def test_student_registration_rejected_when_event_is_full(registration_api):
    client, state = registration_api
    state["user"] = make_user(3, "student")
    state["registration"] = None
    state["registered_count"] = state["event"].capacity

    response = client.post("/events/10/registrations")

    assert response.status_code == 409
    assert response.json()["detail"] == "Event capacity is full"
    assert state["db"].committed is False


def test_cancelled_registration_cannot_be_reactivated_when_event_is_full(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["registration"].status = "Cancelled"
    state["registered_count"] = state["event"].capacity

    response = client.post("/events/10/registrations")

    assert response.status_code == 409
    assert response.json()["detail"] == "Event capacity is full"
    assert state["registration"].status == "Cancelled"
    assert state["db"].committed is False

def test_student_can_cancel_own_registration(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")

    response = client.post("/events/10/registrations/20/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "Cancelled"
    assert state["registration"].status == "Cancelled"
    assert state["db"].committed is True
    assert state["db"].refreshed is True


def test_student_cannot_cancel_another_users_registration(registration_api):
    client, state = registration_api
    state["user"] = make_user(3, "student")

    response = client.post("/events/10/registrations/20/cancel")

    assert response.status_code == 403
    assert state["registration"].status == "Registered"
    assert state["db"].committed is False


def test_cannot_cancel_missing_registration(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["registration"] = None

    response = client.post("/events/10/registrations/20/cancel")

    assert response.status_code == 404
    assert state["db"].committed is False


def test_cannot_cancel_registration_twice(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["registration"].status = "Cancelled"

    response = client.post("/events/10/registrations/20/cancel")

    assert response.status_code == 409
    assert state["registration"].status == "Cancelled"
    assert state["db"].committed is False

def test_cannot_cancel_registration_for_cancelled_event(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["event"].status = "cancelled"

    response = client.post("/events/10/registrations/20/cancel")

    assert response.status_code == 409
    assert state["registration"].status == "Registered"
    assert state["db"].committed is False


def test_cannot_cancel_registration_after_event_ends(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["event"].event_date = date.today() - timedelta(days=1)

    response = client.post("/events/10/registrations/20/cancel")

    assert response.status_code == 409
    assert state["registration"].status == "Registered"
    assert state["db"].committed is False
