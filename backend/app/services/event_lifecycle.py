"""Shared event lifecycle helpers.

Event dates and times are stored as timezone-naive local values in the current
schema. Completion comparisons therefore use the server's local wall clock,
matching the existing registration deadline and event-time conventions.
"""

from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event

ALLOWED_EVENT_STATUS_TRANSITIONS = {
    "draft": {"pending_approval", "cancelled"},
    "pending_approval": {"published", "draft"},
    "published": {"cancelled", "completed"},
    "cancelled": set(),
    "completed": set(),
}


def local_now(now: datetime | None = None) -> datetime:
    """Return a timezone-naive local datetime compatible with Event columns."""
    current = now or datetime.now()
    if current.tzinfo is not None:
        return current.astimezone().replace(tzinfo=None)
    return current


def event_end_datetime(event: Event) -> datetime:
    """Combine the stored event date and end time using the schema's time policy."""
    return datetime.combine(event.event_date, event.end_time.replace(tzinfo=None))


def event_has_ended(event: Event, now: datetime | None = None) -> bool:
    """Whether the event's configured end date/time has passed."""
    return event_end_datetime(event) <= local_now(now)


def can_transition_event_status(current_status: str, new_status: str) -> bool:
    """Return whether a requested status change follows the lifecycle matrix."""
    current = (current_status or "").strip().lower()
    target = (new_status or "").strip().lower()
    return target in ALLOWED_EVENT_STATUS_TRANSITIONS.get(current, set())


async def complete_event_if_due(
    db: AsyncSession,
    event: Event,
    now: datetime | None = None,
) -> bool:
    """Persist Completed for one ended Published event; leave other statuses alone."""
    current = local_now(now)
    if (event.status or "").strip().lower() != "published":
        return False
    if not event_has_ended(event, current):
        return False

    event.status = "completed"
    event.updated_at = current
    await db.commit()
    return True


async def complete_finished_events(
    db: AsyncSession,
    now: datetime | None = None,
) -> int:
    """Persist completion for all ended Published events; safe to run repeatedly."""
    current = local_now(now)
    finished_condition = or_(
        Event.event_date < current.date(),
        and_(
            Event.event_date == current.date(),
            Event.end_time <= current.time(),
        ),
    )
    result = await db.execute(
        select(Event).where(
            func.lower(Event.status) == "published",
            finished_condition,
        )
    )
    events = result.scalars().all()

    changed = 0
    for event in events:
        # Recheck in Python so the behavior is explicit and easy to unit test.
        if (
            (event.status or "").strip().lower() == "published"
            and event_has_ended(event, current)
        ):
            event.status = "completed"
            event.updated_at = current
            changed += 1

    if changed:
        await db.commit()
    return changed
