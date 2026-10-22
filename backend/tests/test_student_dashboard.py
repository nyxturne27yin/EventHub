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



def test_upcoming_registrations_exclude_past_and_cancelled_events(dashboard_api):
    client, state = dashboard_api
    student = state["user"]
    future_registration, future_event = state["rows"][0]

    past_event = make_dashboard_event()
    past_event.id = 11
    past_event.event_date = date.today() - timedelta(days=1)

    cancelled_event = make_dashboard_event()
    cancelled_event.id = 12
    cancelled_event.status = "cancelled"

    completed_event = make_dashboard_event()
    completed_event.id = 13
    completed_event.status = "completed"

    cancelled_registration = EventRegistration(
        id=21, event_id=cancelled_event.id, participant_id=student.id,
        status="Registered", created_at=datetime.now()
    )
    past_registration = EventRegistration(
        id=22, event_id=past_event.id, participant_id=student.id,
        status="Registered", created_at=datetime.now()
    )
    completed_registration = EventRegistration(
        id=23, event_id=completed_event.id, participant_id=student.id,
        status="Registered", created_at=datetime.now()
    )

    state["rows"] = [
        (past_registration, past_event),
        (cancelled_registration, cancelled_event),
        (completed_registration, completed_event),
        (future_registration, future_event),
    ]

    response = client.get("/registrations/me/upcoming")

    assert response.status_code == 200
    assert [item["registration_id"] for item in response.json()] == [20]


def test_upcoming_registrations_are_sorted_earliest_first(dashboard_api):
    client, state = dashboard_api
    student = state["user"]
    later_registration, later_event = state["rows"][0]

    earlier_event = make_dashboard_event()
    earlier_event.id = 11
    earlier_event.event_date = date.today() + timedelta(days=2)
    earlier_registration = EventRegistration(
        id=21, event_id=earlier_event.id, participant_id=student.id,
        status="Registered", created_at=datetime.now()
    )
    state["rows"] = [
        (later_registration, later_event),
        (earlier_registration, earlier_event),
    ]

    response = client.get("/registrations/me/upcoming")

    assert response.status_code == 200
    assert [item["event_id"] for item in response.json()] == [11, 10]


def test_upcoming_registrations_returns_empty_list_when_none(dashboard_api):
    client, state = dashboard_api
    event_registration, event = state["rows"][0]
    event.event_date = date.today() - timedelta(days=1)

    response = client.get("/registrations/me/upcoming")

    assert response.status_code == 200
    assert response.json() == []

def test_organizer_cannot_access_student_dashboard(dashboard_api):
    client, state = dashboard_api
    state["user"] = make_dashboard_user(1, "organizer")

    response = client.get("/registrations/me")

    assert response.status_code == 403


def test_student_dashboard_includes_cancelled_registration_status(
    dashboard_api,
):
    client, state = dashboard_api
    registration, event = state["rows"][0]
    registration.status = "Cancelled"

    response = client.get("/registrations/me")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["registration_status"] == "Cancelled"
