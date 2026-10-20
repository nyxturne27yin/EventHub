from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.event import Event
from app.models.role import Role
from app.models.user import User


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self, event=None):
        self.event = event
        self.committed = False
        self.refreshed = False

    async def execute(self, query):
        return FakeResult(self.event)

    def add(self, instance):
        pass

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


def make_event(organizer_id=1, status="draft"):
    return Event(
        id=10,
        title="Original Event",
        description="Original description",
        category="Academic",
        event_date=date.today() + timedelta(days=10),
        start_time=time(10, 0),
        end_time=time(12, 0),
        mode="Offline",
        venue="UAP Campus",
        meeting_link=None,
        capacity=50,
        registration_deadline=datetime.combine(
            date.today() + timedelta(days=5),
            time(17, 0),
        ),
        status=status,
        organizer_id=organizer_id,
    )


@pytest.fixture
def setup_api():
    state = {
        "user": make_user(),
        "event": make_event(),
        "db": None,
    }

    async def override_get_db():
        db = FakeDB(state["event"])
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


def valid_update(**overrides):
    payload = {"title": "Updated Event"}
    payload.update(overrides)
    return payload


def test_valid_update_persists_changes_and_preserves_unchanged_fields(setup_api):
    client, state = setup_api

    response = client.patch(
        "/events/10",
        json=valid_update(),
    )

    assert response.status_code == 200
    assert response.json()["event"]["title"] == "Updated Event"
    assert response.json()["event"]["description"] == "Original description"
    assert response.json()["event"]["capacity"] == 50
    assert state["event"].title == "Updated Event"
    assert state["db"].committed is True
    assert state["db"].refreshed is True


def test_request_without_authentication_is_rejected():
    app.dependency_overrides.clear()
    client = TestClient(app)

    try:
        response = client.patch(
            "/events/10",
            json=valid_update(),
        )
    finally:
        client.close()
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_student_cannot_update_event(setup_api):
    client, state = setup_api
    state["user"] = make_user(role_name="student")

    response = client.patch(
        "/events/10",
        json=valid_update(),
    )

    assert response.status_code == 403
    assert state["event"].title == "Original Event"
    assert state["db"].committed is False


def test_organizer_cannot_update_another_organizers_event(setup_api):
    client, state = setup_api
    state["event"].organizer_id = 99

    response = client.patch(
        "/events/10",
        json=valid_update(),
    )

    assert response.status_code == 403
    assert state["event"].title == "Original Event"
    assert state["db"].committed is False


def test_nonexistent_event_returns_404(setup_api):
    client, state = setup_api
    state["event"] = None

    response = client.patch(
        "/events/999",
        json=valid_update(),
    )

    assert response.status_code == 404
    assert state["db"].committed is False


def test_invalid_event_id_is_rejected(setup_api):
    client, state = setup_api

    response = client.patch(
        "/events/0",
        json=valid_update(),
    )

    assert response.status_code == 422
    assert state["db"].committed is False


@pytest.mark.parametrize(
    "payload",
    [
        {"title": ""},
        {"capacity": 0},
        {"mode": "Hybrid"},
        {"end_time": "09:00:00"},
        {"event_date": "2000-01-01"},
        {"venue": None},
    ],
)
def test_invalid_update_fields_are_rejected(setup_api, payload):
    client, state = setup_api
    original_title = state["event"].title

    response = client.patch(
        "/events/10",
        json=valid_update(**payload),
    )

    assert response.status_code == 422
    assert state["event"].title == original_title
    assert state["db"].committed is False


def test_empty_update_is_rejected(setup_api):
    client, state = setup_api

    response = client.patch(
        "/events/10",
        json={},
    )

    assert response.status_code == 422
    assert state["db"].committed is False


def test_cancelled_event_cannot_be_updated(setup_api):
    client, state = setup_api
    state["event"].status = "cancelled"

    response = client.patch(
        "/events/10",
        json=valid_update(),
    )

    assert response.status_code == 409
    assert state["event"].title == "Original Event"
    assert state["db"].committed is False


def test_title_update_is_allowed_for_past_event(setup_api):
    client, state = setup_api
    past_date = date.today() - timedelta(days=1)
    state["event"].event_date = past_date

    response = client.patch(
        "/events/10",
        json={"title": "Updated Past Event"},
    )

    assert response.status_code == 200
    assert state["event"].title == "Updated Past Event"
    assert state["event"].event_date == past_date


def test_organizer_can_cancel_own_event(setup_api):
    client, state = setup_api

    response = client.post("/events/10/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert state["event"].status == "cancelled"
    assert state["event"].id == 10
    assert state["db"].committed is True
    assert state["db"].refreshed is True


def test_student_cannot_cancel_event(setup_api):
    client, state = setup_api
    state["user"] = make_user(role_name="student")

    response = client.post("/events/10/cancel")

    assert response.status_code == 403
    assert state["event"].status == "draft"
    assert state["db"].committed is False


def test_organizer_cannot_cancel_another_organizers_event(setup_api):
    client, state = setup_api
    state["event"].organizer_id = 99

    response = client.post("/events/10/cancel")

    assert response.status_code == 403
    assert state["event"].status == "draft"
    assert state["db"].committed is False


def test_cancelling_nonexistent_event_returns_404(setup_api):
    client, state = setup_api
    state["event"] = None

    response = client.post("/events/999/cancel")

    assert response.status_code == 404
    assert state["db"].committed is False


def test_already_cancelled_event_returns_409(setup_api):
    client, state = setup_api
    state["event"].status = "cancelled"

    response = client.post("/events/10/cancel")

    assert response.status_code == 409
    assert response.json()["detail"] == "Event is already cancelled"
    assert state["event"].status == "cancelled"
    assert state["db"].committed is False


def test_invalid_cancel_event_id_is_rejected(setup_api):
    client, state = setup_api

    response = client.post("/events/0/cancel")

    assert response.status_code == 422
    assert state["event"].status == "draft"
    assert state["db"].committed is False


def test_completed_event_cannot_be_updated(setup_api):
    client, state = setup_api
    state["event"].status = "completed"

    response = client.patch(
        "/events/10",
        json=valid_update(),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Completed events cannot be updated"
    assert state["event"].title == "Original Event"
    assert state["db"].committed is False


def test_completed_event_cannot_be_cancelled(setup_api):
    client, state = setup_api
    state["event"].status = "completed"

    response = client.post("/events/10/cancel")

    assert response.status_code == 409
    assert response.json()["detail"] == "Completed events cannot be cancelled."
    assert state["event"].status == "completed"
    assert state["db"].committed is False