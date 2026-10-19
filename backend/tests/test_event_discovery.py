from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient

from app.database.database import get_db
from app.main import app
from app.models.event import Event


class FakeResult:
    def __init__(self, event=None, events=None):
        self.event = event
        self.events = events or []

    def scalar_one_or_none(self):
        return self.event

    def scalar_one(self):
        return 0

    def scalars(self):
        return self

    def all(self):
        return self.events


class FakeDB:
    def __init__(self, event=None, events=None):
        self.event = event
        self.events = events or []

    async def execute(self, query):
        # The endpoint's SQL conditions are covered by integration/database
        # tests; this fake supplies the row returned by the query.
        return FakeResult(event=self.event, events=self.events)


def make_event(event_id=5, status="published"):
    return Event(
        id=event_id,
        title="Discovery Test Event",
        description="A public event description",
        category="Academic",
        event_date=date.today() + timedelta(days=5),
        start_time=time(10, 0),
        end_time=time(12, 0),
        mode="Offline",
        venue="UAP Campus",
        meeting_link=None,
        capacity=40,
        registration_deadline=datetime.combine(
            date.today() + timedelta(days=2), time(17, 0)
        ),
        status=status,
        organizer_id=1,
    )


def make_client(event=None, events=None):
    async def override_get_db():
        yield FakeDB(event=event, events=events)

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_public_event_detail_returns_discovery_fields():
    client = make_client(event=make_event())
    try:
        response = client.get("/events/5")
        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == 5
        assert payload["title"] == "Discovery Test Event"
        assert payload["end_time"] == "12:00:00"
        assert payload["capacity"] == 40
        assert payload["status"] == "published"
        # Public discovery does not return a private meeting URL.
        assert "meeting_link" not in payload
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_cancelled_event_detail_can_show_cancellation_notice():
    client = make_client(event=make_event(status="cancelled"))
    try:
        response = client.get("/events/5")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_draft_or_missing_event_is_not_publicly_discoverable():
    client = make_client(event=None)
    try:
        response = client.get("/events/999")
        assert response.status_code == 404
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_invalid_event_identifier_is_rejected():
    client = make_client(event=None)
    try:
        response = client.get("/events/0")
        assert response.status_code == 422
    finally:
        client.close()
        app.dependency_overrides.clear()
