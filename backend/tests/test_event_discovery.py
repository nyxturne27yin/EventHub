from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.database.database import get_db
from app.main import app
from app.models.event import Event
from app.models.organizer_profile import OrganizerProfile


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
    def __init__(self, event=None, events=None, profile=None):
        self.event = event
        self.events = events or []
        self.profile = profile
        self.committed = False

    async def execute(self, query):
        # Return the correct fake row for event or organizer-profile queries.
        entity = getattr(query, "column_descriptions", [{}])[0].get("entity")

        if entity is OrganizerProfile:
            return FakeResult(event=self.profile)

        if entity is Event:
            query_text = str(query).lower()
            if "events.status =" in query_text and "lower(events.status)" not in query_text:
                now = datetime.now()
                upcoming = [
                    event
                    for event in self.events
                    if (event.status or "").lower() == "published"
                    and (
                        event.event_date > now.date()
                        or (
                            event.event_date == now.date()
                            and event.end_time > now.time()
                        )
                    )
                ]
                return FakeResult(event=self.event, events=upcoming)
            return FakeResult(event=self.event, events=self.events)

        return FakeResult()

    async def commit(self):
        self.committed = True


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


def make_profile(organization_name="CSE Club", department="CSE"):
    # A lightweight fake profile containing the public fields the API uses.
    return SimpleNamespace(
        user_id=1,
        organization_name=organization_name,
        department=department,
    )


def make_client(event=None, events=None, profile=None):
    async def override_get_db():
        yield FakeDB(event=event, events=events, profile=profile)

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_public_event_detail_returns_discovery_fields():
    client = make_client(
        event=make_event(),
        profile=make_profile(),
    )
    try:
        response = client.get("/events/5")
        assert response.status_code == 200

        payload = response.json()
        assert payload["id"] == 5
        assert payload["title"] == "Discovery Test Event"
        assert payload["end_time"] == "12:00:00"
        assert payload["capacity"] == 40
        assert payload["status"] == "published"
        assert payload["organization_name"] == "CSE Club"
        assert payload["department"] == "CSE"

        # Public discovery does not return a private meeting URL.
        assert "meeting_link" not in payload
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_event_detail_works_without_organizer_profile():
    client = make_client(event=make_event(), profile=None)
    try:
        response = client.get("/events/5")

        assert response.status_code == 200
        payload = response.json()
        assert payload["organization_name"] is None
        assert payload["department"] is None
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_cancelled_event_detail_can_show_cancellation_notice():
    client = make_client(
        event=make_event(status="cancelled"),
        profile=make_profile(),
    )
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


def test_event_list_includes_organizer_profile():
    client = make_client(
        events=[make_event()],
        profile=make_profile(
            organization_name="Programming Club",
            department="Computer Science",
        ),
    )
    try:
        response = client.get("/events/")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["organization_name"] == "Programming Club"
        assert payload[0]["department"] == "Computer Science"
    finally:
        client.close()
        app.dependency_overrides.clear()

def test_completed_event_details_remain_available():
    client = make_client(event=make_event(status="completed"))
    try:
        response = client.get("/events/5")

        assert response.status_code == 200
        assert response.json()["status"] == "completed"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_ended_published_event_is_marked_completed_on_detail_access():
    event = make_event(status="published")
    event.event_date = date.today() - timedelta(days=1)
    client = make_client(event=event)
    try:
        response = client.get("/events/5")

        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert event.status == "completed"
    finally:
        client.close()
        app.dependency_overrides.clear()


def test_completed_events_are_excluded_from_upcoming_discovery():
    published_event = make_event(event_id=5, status="published")
    completed_event = make_event(event_id=6, status="completed")
    client = make_client(events=[published_event, completed_event])
    try:
        response = client.get("/events/")

        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [5]
        assert all(item["status"] == "published" for item in response.json())
    finally:
        client.close()
        app.dependency_overrides.clear()
