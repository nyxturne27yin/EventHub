from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.role import Role
from app.models.user import User


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self):
        self.event = None
        self.committed = False
        self.refreshed = False

    async def execute(self, query):
        return FakeResult(None)

    def add(self, instance):
        self.event = instance
        instance.id = 101

    async def commit(self):
        self.committed = True

    async def refresh(self, instance):
        self.refreshed = True


def make_user(role_name="organizer"):
    role = Role(id=2 if role_name == "organizer" else 1, name=role_name)
    user = User(
        id=1,
        name="Test Organizer",
        email="12345678@uap-bd.edu",
        password_hash="test-hash",
        role_id=role.id,
        is_active=True,
    )
    user.role = role
    return user


def valid_payload(**overrides):
    payload = {
        "title": "Test Event",
        "description": "Event for testing",
        "category": "Academic",
        "event_date": (date.today() + timedelta(days=10)).isoformat(),
        "start_time": "10:00:00",
        "end_time": "12:00:00",
        "mode": "Offline",
        "venue": "UAP Campus",
        "meeting_link": None,
        "capacity": 50,
        "registration_deadline": datetime.combine(
            date.today() + timedelta(days=5),
            time(17, 0),
        ).isoformat(),
        "status": "draft",
    }
    payload.update(overrides)
    return payload


def setup_client(role_name="organizer"):
    state = {"user": make_user(role_name), "db": FakeDB()}

    async def override_get_db():
        yield state["db"]

    async def override_get_current_user():
        return state["user"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    return TestClient(app), state


def teardown_client(client):
    client.close()
    app.dependency_overrides.clear()


def test_organizer_can_create_event():
    client, state = setup_client()

    try:
        response = client.post("/events/", json=valid_payload())

        assert response.status_code == 201
        assert response.json()["event"]["title"] == "Test Event"
        assert state["db"].event.organizer_id == state["user"].id
        assert state["db"].committed is True
        assert state["db"].refreshed is True
    finally:
        teardown_client(client)


def test_student_cannot_create_event():
    client, state = setup_client("student")

    try:
        response = client.post("/events/", json=valid_payload())

        assert response.status_code == 403
        assert state["db"].event is None
    finally:
        teardown_client(client)


def test_invalid_capacity_is_rejected():
    client, state = setup_client()

    try:
        response = client.post(
            "/events/",
            json=valid_payload(capacity=0),
        )

        assert response.status_code == 422
        assert state["db"].event is None
    finally:
        teardown_client(client)


def test_end_time_must_be_after_start_time():
    client, state = setup_client()

    try:
        response = client.post(
            "/events/",
            json=valid_payload(
                start_time="12:00:00",
                end_time="10:00:00",
            ),
        )

        assert response.status_code == 422
        assert state["db"].event is None
    finally:
        teardown_client(client)
