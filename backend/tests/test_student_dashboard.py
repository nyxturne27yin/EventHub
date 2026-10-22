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


class DashboardResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class DashboardFakeDB:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, query):
        return DashboardResult(self.rows)


def make_dashboard_user(user_id=2, role_name="student"):
    user = User(
        id=user_id,
        name=f"Dashboard User {user_id}",
        email=f"{user_id}234567@uap-bd.edu",
        password_hash="test-hash",
        role_id=1 if role_name == "student" else 2,
        is_active=True,
    )
    user.role = Role(id=user.role_id, name=role_name)
    return user


def make_dashboard_event():
    return Event(
        id=10,
        title="Dashboard Test Event",
        description="Event for dashboard testing",
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
        organizer_id=1,
    )


@pytest.fixture
def dashboard_api():
    student = make_dashboard_user()
    event = make_dashboard_event()
    registration = EventRegistration(
        id=20,
        event_id=event.id,
        participant_id=student.id,
        status="Registered",
        created_at=datetime.now(),
    )

    state = {
        "user": student,
        "rows": [(registration, event)],
    }

    async def override_get_db():
        yield DashboardFakeDB(state["rows"])

    async def override_get_current_user():
        return state["user"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)
    yield client, state

    client.close()
    app.dependency_overrides.clear()


def test_student_can_view_own_dashboard_registrations(dashboard_api):
    client, state = dashboard_api

    response = client.get("/registrations/me")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["registration_id"] == 20
    assert data[0]["event_id"] == 10
    assert data[0]["title"] == "Dashboard Test Event"
    assert data[0]["registration_status"] == "Registered"


def test_student_dashboard_returns_empty_list_without_registrations(
    dashboard_api,
):
    client, state = dashboard_api
    state["rows"] = []

    response = client.get("/registrations/me")

    assert response.status_code == 200
    assert response.json() == []


def test_organizer_cannot_access_student_dashboard(dashboard_api):
    client, state = dashboard_api
    state["user"] = make_dashboard_user(1, "organizer")

    response = client.get("/registrations/me")

    assert response.status_code == 403
