import asyncio
from datetime import date, datetime, time, timezone
from types import SimpleNamespace

from app.services.event_lifecycle import (
    can_transition_event_status,
    complete_event_if_due,
    complete_finished_events,
    event_has_ended,
    local_now,
)


class FakeResult:
    def __init__(self, events):
        self.events = events

    def scalars(self):
        return self

    def all(self):
        return self.events


class FakeDB:
    def __init__(self, events):
        self.events = events
        self.commit_count = 0
        self.executed = []

    async def execute(self, statement):
        self.executed.append(statement)
        return FakeResult(self.events)

    async def commit(self):
        self.commit_count += 1


def make_event(status="published", event_date=None, end_time=time(12, 0)):
    return SimpleNamespace(
        id=1,
        status=status,
        event_date=event_date or date.today(),
        end_time=end_time,
        updated_at=None,
    )


def test_event_is_not_completed_before_its_end_time():
    event = make_event(event_date=date(2026, 10, 20), end_time=time(15, 0))

    assert not event_has_ended(event, datetime(2026, 10, 20, 14, 59, 59))


def test_event_is_completed_at_its_end_time_boundary():
    event = make_event(event_date=date(2026, 10, 20), end_time=time(15, 0))

    assert event_has_ended(event, datetime(2026, 10, 20, 15, 0))


def test_aware_now_is_normalized_to_naive_local_time():
    normalized = local_now(datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc))

    assert normalized.tzinfo is None


def test_only_ended_published_event_is_completed_and_persisted():
    event = make_event(
        status="published",
        event_date=date(2026, 10, 19),
        end_time=time(23, 59),
    )
    db = FakeDB([event])

    changed = asyncio.run(
        complete_event_if_due(db, event, datetime(2026, 10, 20, 10, 0))
    )

    assert changed is True
    assert event.status == "completed"
    assert event.updated_at == datetime(2026, 10, 20, 10, 0)
    assert db.commit_count == 1


def test_cancelled_event_is_never_completed_by_time_processing():
    event = make_event(
        status="cancelled",
        event_date=date(2026, 10, 19),
        end_time=time(23, 59),
    )
    db = FakeDB([event])

    changed = asyncio.run(
        complete_event_if_due(db, event, datetime(2026, 10, 20, 10, 0))
    )

    assert changed is False
    assert event.status == "cancelled"
    assert db.commit_count == 0


def test_bulk_completion_preserves_cancelled_and_future_events_and_is_idempotent():
    past_published = make_event(
        status="published",
        event_date=date(2026, 10, 19),
        end_time=time(23, 59),
    )
    past_cancelled = make_event(
        status="cancelled",
        event_date=date(2026, 10, 19),
        end_time=time(23, 59),
    )
    future_published = make_event(
        status="published",
        event_date=date(2026, 10, 21),
        end_time=time(12, 0),
    )
    already_completed = make_event(
        status="completed",
        event_date=date(2026, 10, 19),
        end_time=time(23, 59),
    )
    db = FakeDB(
        [past_published, past_cancelled, future_published, already_completed]
    )
    now = datetime(2026, 10, 20, 10, 0)

    first_count = asyncio.run(complete_finished_events(db, now))
    second_count = asyncio.run(complete_finished_events(db, now))

    assert first_count == 1
    assert second_count == 0
    assert past_published.status == "completed"
    assert past_cancelled.status == "cancelled"
    assert future_published.status == "published"
    assert already_completed.status == "completed"
    assert db.commit_count == 1


def test_status_transition_matrix_keeps_cancelled_and_completed_terminal():
    assert can_transition_event_status("draft", "published")
    assert can_transition_event_status("published", "cancelled")
    assert not can_transition_event_status("cancelled", "published")
    assert not can_transition_event_status("completed", "cancelled")
    assert not can_transition_event_status("draft", "completed")
