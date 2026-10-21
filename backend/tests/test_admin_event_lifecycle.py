from datetime import date, datetime, time, timedelta

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
    def __init__(self, event):
        self.event = event
        self.committed = False
        self.refreshed = False

    async def execute(self, statement):
        return FakeResult(self.event)

    async def commit(self):
        self.committed = True

    async def refresh(self, instance):
        self.refreshed = True


def make_event(status="published", event_date=None, end_time=time(23, 59)):
    return Event(
        id=10,
        title="Lifecycle Test Event",
        description="Event lifecycle test",
        category="Academic",
        event_date=event_date or date.today() + timedelta(days=1),
        start_time=time(10, 0),
        end_time=end_time,
        mode="Offline",
        venue="UAP Campus",
        meeting_link=None,
        capacity=20,
        registration_deadline=datetime.now() + timedelta(hours=1),
        status=status,
        organizer_id=2,
    )


def make_admin():
    user = User(
        id=1,
        name="Test Administrator",
        email="12345678@uap-bd.edu",
        password_hash="test-hash",
        role_id=3,
        is_active=True,
    )
    user.role = Role(id=3, name="administrator")
    return user


def make_client(event):
    state = {"db": FakeDB(event)}

    async def override_get_db():
        yield state["db"]

    async def override_get_current_user():
        return make_admin()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app), state


def test_admin_cannot_complete_event_before_end_time():
    event = make_event(status="published")
    client, state = make_client(event)
    try:
        response = client.patch(
            "/admin/events/10/status",
            json={"status": "completed"},
        )

        assert response.status_code == 409
        assert "after its end date and time" in response.json()["detail"]
        assert event.status == "published"
        assert state["db"].committed is False
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_admin_completion_request_is_idempotent_after_event_end():
    event = make_event(
        status="published",
        event_date=date.today() - timedelta(days=1),
    )
    client, state = make_client(event)
    try:
        response = client.patch(
            "/admin/events/10/status",
            json={"status": "completed"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert event.status == "completed"
        assert state["db"].committed is True
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_admin_cannot_reclassify_cancelled_event_as_completed():
    event = make_event(
        status="cancelled",
        event_date=date.today() - timedelta(days=1),
    )
    client, state = make_client(event)
    try:
        response = client.patch(
            "/admin/events/10/status",
            json={"status": "completed"},
        )

        assert response.status_code == 409
        assert event.status == "cancelled"
        assert state["db"].committed is False
    finally:
        client.close()
        app.dependency_overrides.clear()
