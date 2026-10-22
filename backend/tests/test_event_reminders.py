from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.event_reminders import (
    build_reminder_message,
    is_reminder_due,
    reminder_deduplication_key,
)


def test_reminder_is_due_at_24_hour_mark():
    now = datetime(2026, 10, 22, 10, 0)
    assert is_reminder_due(now + timedelta(hours=24), now)


def test_reminder_is_due_within_scheduler_window():
    now = datetime(2026, 10, 22, 10, 0)
    assert is_reminder_due(now + timedelta(hours=24, minutes=14), now)
    assert not is_reminder_due(now + timedelta(hours=24, minutes=16), now)


def test_too_close_or_past_event_is_not_due():
    now = datetime(2026, 10, 22, 10, 0)
    assert not is_reminder_due(now + timedelta(hours=23), now)
    assert not is_reminder_due(now - timedelta(minutes=1), now)


def test_reminder_key_is_specific_to_event_user_and_schedule():
    event = SimpleNamespace(
        id=7,
        event_date=datetime(2026, 10, 23).date(),
        start_time=datetime(2026, 10, 23, 10, 0).time(),
    )
    registration = SimpleNamespace(participant_id=12)
    key = reminder_deduplication_key(event, registration)
    assert key == "event-reminder:7:12:2026-10-23:10:00:00"


def test_message_includes_date_time_and_online_details():
    event = SimpleNamespace(
        title="Tech Talk",
        event_date=datetime(2026, 10, 23).date(),
        start_time=datetime(2026, 10, 23, 10, 0).time(),
        mode="online",
        venue=None,
        meeting_link="https://example.com/meeting",
    )
    message = build_reminder_message(event)
    assert "Tech Talk" in message
    assert "2026-10-23" in message
    assert "10:00:00" in message
    assert "https://example.com/meeting" in message
