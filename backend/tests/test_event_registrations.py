from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.event import Event
from app.models.notification import Notification
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
    def __init__(
        self,
        event,
        registration,
        participant,
        registered_count=0,
        state=None,
    ):
        self.event = event
        self.registration = registration
        self.participant = participant
        self.registered_count = registered_count
        self.state = state
        self.initial_status = (
            registration.status if registration else None
        )
        self.committed = False
        self.refreshed = False
        self.added_objects = []

    async def execute(self, query):
        entities = [
            description["entity"]
            for description in query.column_descriptions
        ]

        if (
            len(entities) > 1
            and entities[0] is EventRegistration
            and entities[1] is Event
        ):
            return FakeResult(
                rows=[
                    (self.registration, self.event)
                ]
                if self.registration and self.event
                else []
            )

        if entities[0] is Event:
            return FakeResult(self.event)

        if "count(" in str(query).lower():
            return FakeResult(self.registered_count)

        if len(entities) > 1 and entities[1] is User:
            return FakeResult(
                rows=[
                    (self.registration, self.participant)
                ]
                if self.registration and self.participant
                else []
            )

        return FakeResult(self.registration)

    def add(self, instance):
        self.added_objects.append(instance)

        if isinstance(instance, EventRegistration):
            self.registration = instance

            if self.state is not None:
                self.state["registration"] = instance

        elif isinstance(instance, Notification):
            if self.state is not None:
                self.state["notification"] = instance

    async def commit(self):
        self.committed = True

        if (
            self.initial_status == "Registered"
            and self.registration
            and self.registration.status == "Cancelled"
        ):
            self.registered_count = max(
                0,
                self.registered_count - 1,
            )

            if self.state is not None:
                self.state["registered_count"] = (
                    self.registered_count
                )

        self.initial_status = (
            self.registration.status
            if self.registration
            else None
        )

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
        "registered_count": 0,
        "notification": None,
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
            state=state,
        )
        state["db"] = db
        yield db

    async def override_get_current_user():
        return state["user"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = (
        override_get_current_user
    )

    client = TestClient(app)
    yield client, state

    client.close()
    app.dependency_overrides.clear()


def test_student_can_cancel_own_registration(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")

    response = client.post(
        "/events/10/registrations/20/cancel"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Cancelled"
    assert state["registration"].status == "Cancelled"
    assert state["db"].committed is True
    assert state["db"].refreshed is True


def test_student_cannot_cancel_another_users_registration(
    registration_api,
):
    client, state = registration_api
    state["user"] = make_user(3, "student")

    response = client.post(
        "/events/10/registrations/20/cancel"
    )

    assert response.status_code == 403
    assert state["registration"].status == "Registered"
    assert state["db"].committed is False


def test_cannot_cancel_missing_registration(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["registration"] = None

    response = client.post(
        "/events/10/registrations/20/cancel"
    )

    assert response.status_code == 404
    assert state["db"].committed is False


def test_cannot_cancel_registration_twice(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["registration"].status = "Cancelled"

    response = client.post(
        "/events/10/registrations/20/cancel"
    )

    assert response.status_code == 409
    assert state["registration"].status == "Cancelled"
    assert state["db"].committed is False


def test_cannot_cancel_registration_for_cancelled_event(
    registration_api,
):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["event"].status = "cancelled"

    response = client.post(
        "/events/10/registrations/20/cancel"
    )

    assert response.status_code == 409
    assert state["registration"].status == "Registered"
    assert state["db"].committed is False


def test_cannot_cancel_registration_after_event_ends(
    registration_api,
):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["event"].event_date = date.today() - timedelta(days=1)

    response = client.post(
        "/events/10/registrations/20/cancel"
    )

    assert response.status_code == 409
    assert state["event"].status == "completed"
    assert state["registration"].status == "Registered"
    assert state["db"].committed is True


def test_organizer_can_view_participant_status(registration_api):
    client, _ = registration_api

    response = client.get("/events/10/participants")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "Registered"
    assert (
        response.json()[0]["participant_email"]
        == "2234567@uap-bd.edu"
    )


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


def test_organizer_cannot_manage_another_organizers_participants(
    registration_api,
):
    client, state = registration_api
    state["event"].organizer_id = 99

    response = client.patch(
        "/events/10/registrations/20/status",
        json={"status": "Cancelled"},
    )

    assert response.status_code == 403
    assert state["registration"].status == "Registered"


def test_student_registration_rejected_when_event_is_full(
    registration_api,
):
    client, state = registration_api
    state["user"] = make_user(3, "student")
    state["registration"] = None
    state["registered_count"] = state["event"].capacity

    response = client.post("/events/10/registrations")

    assert response.status_code == 409
    assert response.json()["detail"] == "Event capacity is full"
    assert state["db"].committed is False


def test_cancelled_registration_cannot_be_reactivated_when_event_is_full(
    registration_api,
):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["registration"].status = "Cancelled"
    state["registered_count"] = state["event"].capacity

    response = client.post("/events/10/registrations")

    assert response.status_code == 409
    assert response.json()["detail"] == "Event capacity is full"
    assert state["registration"].status == "Cancelled"
    assert state["db"].committed is False


def test_student_registration_is_rejected_when_event_is_completed(
    registration_api,
):
    client, state = registration_api
    state["user"] = make_user(3, "student")
    state["registration"] = None
    state["event"].status = "completed"

    response = client.post("/events/10/registrations")

    assert response.status_code == 409
    assert "completed" in response.json()["detail"].lower()
    assert state["event"].status == "completed"
    assert state["db"].committed is False


def test_ended_published_event_is_completed_before_registration_is_rejected(
    registration_api,
):
    client, state = registration_api
    state["user"] = make_user(3, "student")
    state["registration"] = None
    state["event"].event_date = date.today() - timedelta(days=1)
    state["event"].status = "published"

    response = client.post("/events/10/registrations")

    assert response.status_code == 409
    assert "completed" in response.json()["detail"].lower()
    assert state["event"].status == "completed"
    assert state["db"].committed is True
    assert state["registration"] is None


def test_student_can_view_multiple_registration_statuses(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")

    first_event = state["event"]
    second_event = make_event()
    second_event.id = 11
    second_event.title = "Second Test Event"

    first_registration = state["registration"]
    first_registration.status = "Registered"

    second_registration = EventRegistration(
        id=21,
        event_id=11,
        participant_id=2,
        status="Cancelled",
        created_at=datetime.now(),
    )

    async def override_get_db():
        class MultipleRegistrationDB(FakeDB):
            async def execute(self, query):
                entities = [
                    description["entity"]
                    for description in query.column_descriptions
                ]

                if (
                    len(entities) > 1
                    and entities[0] is EventRegistration
                    and entities[1] is Event
                ):
                    return FakeResult(
                        rows=[
                            (first_registration, first_event),
                            (second_registration, second_event),
                        ]
                    )

                return await super().execute(query)

        db = MultipleRegistrationDB(
            first_event,
            first_registration,
            state["participant"],
            state=state,
        )
        state["db"] = db
        yield db

    original_get_db_override = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/registrations/me")
    finally:
        app.dependency_overrides[get_db] = original_get_db_override

    assert response.status_code == 200
    registrations = response.json()
    assert len(registrations) == 2
    registrations_by_event = {
        item["event_id"]: item["registration_status"]
        for item in registrations
    }
    assert registrations_by_event == {
        10: "Registered",
        11: "Cancelled",
    }


@pytest.mark.parametrize("registration_status", ["Registered", "Cancelled"])
def test_student_can_view_own_registration_status(
    registration_api,
    registration_status,
):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["registration"].status = registration_status

    response = client.get("/registrations/me")

    assert response.status_code == 200
    registrations = response.json()
    assert len(registrations) == 1
    assert registrations[0]["registration_id"] == 20
    assert registrations[0]["event_id"] == 10
    assert registrations[0]["registration_status"] == registration_status


def test_student_can_view_registration_history_for_completed_event(
    registration_api,
):
    client, state = registration_api
    state["user"] = make_user(2, "student")
    state["event"].status = "completed"
    state["event"].event_date = date.today() - timedelta(days=1)

    try:
        response = client.get("/registrations/me")
    finally:
        client.close()

    assert response.status_code == 200
    registrations = response.json()

    assert len(registrations) == 1
    record = registrations[0]
    assert record["registration_id"] == 20
    assert record["event_id"] == 10
    assert record["registration_status"] == "Registered"
    assert record["title"] == "Test Event"
    assert record["description"] == "Test description"


def test_organizer_cannot_view_student_registration_history(
    registration_api,
):
    client, _ = registration_api

    response = client.get("/registrations/me")

    assert response.status_code == 403


# EV-115: Registration creation and validation tests

def test_student_can_register_for_published_event(registration_api):
    client, state = registration_api
    state["user"] = make_user(3, "student")
    state["registration"] = None

    response = client.post("/events/10/registrations")

    assert response.status_code == 201
    assert response.json()["event_id"] == 10
    assert response.json()["participant_id"] == 3
    assert response.json()["status"] == "Registered"
    assert state["registration"] is not None
    assert state["registration"].status == "Registered"
    assert state["notification"] is not None
    assert state["notification"].title == "Registration Successful"
    assert state["db"].committed is True
    assert state["db"].refreshed is True


def test_organizer_cannot_register_as_student(registration_api):
    client, state = registration_api
    state["user"] = make_user(1, "organizer")
    state["registration"] = None

    response = client.post("/events/10/registrations")

    assert response.status_code == 403
    assert state["registration"] is None
    assert state["db"].committed is False


def test_registration_rejected_after_deadline(registration_api):
    client, state = registration_api
    state["user"] = make_user(3, "student")
    state["registration"] = None
    state["event"].registration_deadline = (
        datetime.now() - timedelta(days=1)
    )

    response = client.post("/events/10/registrations")

    assert response.status_code == 409
    assert response.json()["detail"] == "Registration deadline has passed"
    assert state["registration"] is None
    assert state["db"].committed is False


def test_duplicate_registration_is_rejected(registration_api):
    client, state = registration_api
    state["user"] = make_user(2, "student")

    response = client.post("/events/10/registrations")

    assert response.status_code == 409
    assert response.json()["detail"] == "Already registered for this event"
    assert state["registration"].status == "Registered"
    assert state["db"].committed is False


def test_registration_rejected_when_event_does_not_exist(registration_api):
    client, state = registration_api
    state["user"] = make_user(3, "student")
    state["event"] = None
    state["registration"] = None

    response = client.post("/events/10/registrations")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"
    assert state["registration"] is None
    assert state["db"].committed is False


def test_registration_rejected_for_cancelled_event(registration_api):
    client, state = registration_api
    state["user"] = make_user(3, "student")
    state["registration"] = None
    state["event"].status = "cancelled"

    response = client.post("/events/10/registrations")

    assert response.status_code == 409
    assert "cancelled" in response.json()["detail"].lower()
    assert state["registration"] is None
    assert state["db"].committed is False