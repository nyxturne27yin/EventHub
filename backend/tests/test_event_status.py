import asyncio
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.event_status import can_transition_event_status
from app.routers.admin import (
    EventStatusUpdateRequest,
    update_event_status,
)


class FakeResult:
    def __init__(self, event):
        self.event = event

    def scalar_one_or_none(self):
        return self.event


class FakeDB:
    def __init__(self, event):
        self.event = event
        self.execute = AsyncMock(return_value=FakeResult(event))
        self.commit = AsyncMock()
        self.refresh = AsyncMock()



def make_event(status="draft"):
    return SimpleNamespace(
        id=1,
        status=status,
        event_date=date.today() + timedelta(days=1),
        end_time=time(23, 59),
        updated_at=None,
    )



@pytest.mark.parametrize(
    ("current", "target", "expected"),
    [
        ("draft", "pending_approval", True),
        ("draft", "published", False),
        ("draft", "cancelled", True),
        ("pending_approval", "published", True),
        ("pending_approval", "draft", True),
        ("pending_approval", "cancelled", False),
        ("published", "completed", True),
        ("published", "cancelled", True),
        ("cancelled", "published", False),
        ("completed", "cancelled", False),
        ("completed", "published", False),
        ("draft", "completed", False),
    ],
)
def test_lifecycle_transition_rules(current, target, expected):
    assert can_transition_event_status(current, target) is expected


def test_admin_can_approve_pending_event():
    event = make_event("pending_approval")
    db = FakeDB(event)

    result = asyncio.run(
        update_event_status(
            payload=EventStatusUpdateRequest(status="published"),
            event_id=1,
            db=db,
        )
    )

    assert result["status"] == "published"
    assert event.status == "published"

def test_admin_can_reject_pending_event_to_draft():
    event = make_event("pending_approval")
    db = FakeDB(event)

    result = asyncio.run(
        update_event_status(
            payload=EventStatusUpdateRequest(status="draft"),
            event_id=1,
            db=db,
        )
    )

    assert result["status"] == "draft"
    assert event.status == "draft"

def test_admin_cannot_repeat_current_status():
    db = FakeDB(make_event("published"))

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            update_event_status(
                payload=EventStatusUpdateRequest(status="published"),
                event_id=1,
                db=db,
            )
        )

    assert error.value.status_code == 409
    db.commit.assert_not_awaited()


def test_admin_cannot_change_completed_event():
    db = FakeDB(make_event("completed"))

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            update_event_status(
                payload=EventStatusUpdateRequest(status="cancelled"),
                event_id=1,
                db=db,
            )
        )

    assert error.value.status_code == 409
    db.commit.assert_not_awaited()


def test_admin_cannot_reopen_cancelled_event():
    db = FakeDB(make_event("cancelled"))

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            update_event_status(
                payload=EventStatusUpdateRequest(status="published"),
                event_id=1,
                db=db,
            )
        )

    assert error.value.status_code == 409
    db.commit.assert_not_awaited()


def test_admin_status_update_returns_404_for_missing_event():
    db = FakeDB(None)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            update_event_status(
                payload=EventStatusUpdateRequest(status="published"),
                event_id=1,
                db=db,
            )
        )

    assert error.value.status_code == 404
    db.commit.assert_not_awaited()


def test_status_request_rejects_unknown_status():
    with pytest.raises(ValidationError):
        EventStatusUpdateRequest(status="archived")
