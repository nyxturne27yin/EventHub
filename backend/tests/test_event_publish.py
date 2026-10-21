from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.event import Event
from app.models.role import Role
from app.models.user import User


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self, event=None):
        self.event = event
        self.committed = False
        self.refreshed = False

    async def execute(self, query):
        entity = getattr(query, "column_descriptions", [{}])[0].get("entity")
        return FakeResult(self.event if entity is Event else None)

    async def commit(self):
        self.committed = True

    async def refresh(self, instance):
        self.refreshed = True


def make_event(status="draft", organizer_id=1, **overrides):
    values = dict(
        id=7,
        title="Publish Test Event",
        description="A valid event for publishing",
        category="Academic",
        event_date=date.today() + timedelta(days=10),
        start_time=time(10, 0),
        end_time=time(12, 0),
        mode="Offline",
        venue="Campus",
        meeting_link=None,
        capacity=30,
        registration_deadline=datetime.combine(
            date.today() + timedelta(days=5), time(17, 0)
        ),
        status=status,
        organizer_id=organizer_id,
        updated_at=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_user(role_name="organizer", user_id=1):
    role = Role(id=2 if role_name == "organizer" else 1, name=role_name)
    user = User(
        id=user_id,
        name="Test User",
        email=f"{user_id}@example.com",
        password_hash="not-used",
        role_id=role.id,
        is_active=True,
    )
    user.role = role
    return user


def setup_client(event, user=None):
    state = {"db": FakeDB(event)}

    async def override_get_db():
        yield state["db"]

    async def override_get_current_user():
        return user or make_user()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app), state


def teardown(client):
    client.close()
    app.dependency_overrides.clear()


def test_owner_can_publish_draft_and_status_is_persisted():
    event = make_event()
    client, state = setup_client(event)
    try:
        response = client.post("/events/7/publish")
        assert response.status_code == 200
        assert response.json()["event"]["status"] == "published"
        assert event.status == "published"
        assert state["db"].committed
        assert state["db"].refreshed
    finally:
        teardown(client)


def test_organizer_cannot_publish_another_organizers_event():
    client, state = setup_client(make_event(organizer_id=99))
    try:
        response = client.post("/events/7/publish")
        assert response.status_code == 403
        assert state["db"].committed is False
    finally:
        teardown(client)


def test_student_cannot_publish_event():
    client, state = setup_client(make_event(), make_user("student"))
    try:
        response = client.post("/events/7/publish")
        assert response.status_code == 403
        assert state["db"].committed is False
    finally:
        teardown(client)


def test_cancelled_and_completed_events_cannot_be_published():
    for status_value in ("cancelled", "completed", "published"):
        client, state = setup_client(make_event(status=status_value))
        try:
            response = client.post("/events/7/publish")
            assert response.status_code == 409
            assert state["db"].committed is False
        finally:
            teardown(client)


def test_invalid_event_prerequisite_prevents_publishing():
    event = make_event(venue=None)
    client, state = setup_client(event)
    try:
        response = client.post("/events/7/publish")
        assert response.status_code == 422
        assert event.status == "draft"
        assert state["db"].committed is False
    finally:
        teardown(client)


def test_missing_event_returns_404():
    client, state = setup_client(None)
    try:
        response = client.post("/events/7/publish")
        assert response.status_code == 404
        assert state["db"].committed is False
    finally:
        teardown(client)


def test_unauthenticated_request_cannot_publish_event():
    event = make_event()
    client, state = setup_client(event)
    app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.post("/events/7/publish")
        assert response.status_code == 401
        assert event.status == "draft"
        assert state["db"].committed is False
    finally:
        teardown(client)
