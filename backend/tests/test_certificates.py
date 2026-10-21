from datetime import date, datetime, time, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.certificate import Certificate
from app.models.event import Event
from app.models.registration import EventRegistration
from app.models.role import Role
from app.models.user import User


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDB:
    def __init__(self, event, student, registration, existing_certificate=None):
        self.event = event
        self.student = student
        self.registration = registration
        self.existing_certificate = existing_certificate
        self.added = None
        self.commit_count = 0

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Event:
            return FakeResult(self.event)
        if entity is User:
            return FakeResult(self.student)
        if entity is EventRegistration:
            registration = self.registration
            if registration and registration.status == "Registered":
                return FakeResult(registration)
            return FakeResult(None)
        if entity is Certificate:
            return FakeResult(self.existing_certificate)
        return FakeResult(None)

    def add(self, instance):
        self.added = instance

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, instance):
        if isinstance(instance, Certificate):
            instance.certificate_id = str(uuid4())
            instance.issued_at = datetime.now()


def make_user(user_id, role_name):
    user = User(
        id=user_id,
        name=f"Test {role_name.title()}",
        email=f"{user_id}234567@uap-bd.edu",
        password_hash="test-hash",
        role_id=2 if role_name == "organizer" else 1,
        is_active=True,
    )
    user.role = Role(id=user.role_id, name=role_name)
    return user


def make_event(status="completed", event_date=None):
    return Event(
        id=10,
        title="Certificate Event",
        description="Certificate test event",
        category="Academic",
        event_date=event_date or date.today() - timedelta(days=1),
        start_time=time(10, 0),
        end_time=time(12, 0),
        mode="Offline",
        venue="UAP Campus",
        meeting_link=None,
        capacity=30,
        registration_deadline=datetime.now() - timedelta(days=2),
        status=status,
        organizer_id=1,
    )


def make_client(event, registration_status="Registered"):
    organizer = make_user(1, "organizer")
    student = make_user(2, "student")
    registration = EventRegistration(
        id=5,
        event_id=event.id,
        participant_id=student.id,
        status=registration_status,
        created_at=datetime.now(),
    )
    db = FakeDB(event, student, registration)

    async def override_get_db():
        yield db

    async def override_get_current_user():
        return organizer

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app), db, registration


def test_ended_published_event_is_completed_before_certificate_generation():
    event = make_event(status="published")
    client, db, registration = make_client(event)
    try:
        response = client.post(
            "/certificates/events/10/generate",
            json={"student_id": 2, "category": "Academic"},
        )

        assert response.status_code == 201
        assert event.status == "completed"
        assert registration.status == "Registered"
        assert response.json()["certificate"]["event_id"] == 10
        assert db.added is not None
        assert db.commit_count == 2
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_certificate_is_not_issued_for_cancelled_registration():
    event = make_event(status="completed")
    client, db, _ = make_client(event, registration_status="Cancelled")
    try:
        response = client.post(
            "/certificates/events/10/generate",
            json={"student_id": 2, "category": "Academic"},
        )

        assert response.status_code == 409
        assert "active registration" in response.json()["detail"]
        assert db.added is None
        assert db.commit_count == 0
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_certificate_is_not_issued_before_event_completion():
    event = make_event(
        status="published",
        event_date=date.today() + timedelta(days=1),
    )
    client, db, _ = make_client(event)
    try:
        response = client.post(
            "/certificates/events/10/generate",
            json={"student_id": 2, "category": "Academic"},
        )

        assert response.status_code == 409
        assert event.status == "published"
        assert db.added is None
        assert db.commit_count == 0
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_stale_completed_status_does_not_allow_certificate_before_event_end():
    event = make_event(
        status="completed",
        event_date=date.today() + timedelta(days=1),
    )
    client, db, _ = make_client(event)
    try:
        response = client.post(
            "/certificates/events/10/generate",
            json={"student_id": 2, "category": "Academic"},
        )

        assert response.status_code == 409
        assert "after an event has completed" in response.json()["detail"]
        assert db.added is None
        assert db.commit_count == 0
    finally:
        client.close()
        app.dependency_overrides.clear()
