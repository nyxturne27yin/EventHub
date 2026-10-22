"""Send event reminders approximately 24 hours before published events.

Run this module every 15 minutes with an external scheduler.
"""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import AsyncSessionLocal
from app.models.event import Event
from app.models.notification import Notification
from app.models.registration import EventRegistration
from app.services.event_lifecycle import local_now


REMINDER_LEAD = timedelta(hours=24)
DEFAULT_LOOKAHEAD = timedelta(minutes=15)


def is_reminder_due(
    event_start: datetime,
    now: datetime,
    lookahead: timedelta = DEFAULT_LOOKAHEAD,
) -> bool:
    """True only during the 15-minute window before the 24-hour reminder point."""
    reminder_at = event_start - REMINDER_LEAD
    return now <= reminder_at < now + lookahead


def reminder_deduplication_key(event: Event, registration: EventRegistration) -> str:
    return (
        f"event-reminder:{event.id}:{registration.participant_id}:"
        f"{event.event_date.isoformat()}:{event.start_time.isoformat()}"
    )


def build_reminder_message(event: Event) -> str:
    details = [f"Mode: {event.mode}"]
    if event.venue:
        details.append(f"Venue: {event.venue}")
    if event.meeting_link:
        details.append(f"Meeting link: {event.meeting_link}")
    if not event.venue and not event.meeting_link:
        details.append("Venue/meeting details: To be announced")

    return (
        f"Reminder: '{event.title}' starts in approximately 24 hours. "
        f"Date: {event.event_date}; Time: {event.start_time}. "
        + "; ".join(details)
    )


async def send_due_event_reminders(
    db: AsyncSession,
    now: datetime | None = None,
    lookahead: timedelta = DEFAULT_LOOKAHEAD,
) -> int:
    """Create reminders for active registrations, safely skipping duplicate keys."""
    current = local_now(now)
    horizon = current + REMINDER_LEAD + lookahead

    result = await db.execute(
        select(Event).where(
            func.lower(Event.status) == "published",
            Event.event_date >= current.date(),
            Event.event_date <= horizon.date(),
        )
    )
    events = result.scalars().all()
    created = 0

    for event in events:
        event_start = datetime.combine(
            event.event_date, event.start_time.replace(tzinfo=None)
        )
        if event_start <= current or not is_reminder_due(
            event_start, current, lookahead
        ):
            continue

        registrations_result = await db.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event.id,
                func.lower(EventRegistration.status) == "registered",
            )
        )

        for registration in registrations_result.scalars().all():
            key = reminder_deduplication_key(event, registration)
            existing = await db.execute(
                select(Notification.id).where(
                    Notification.deduplication_key == key
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            notification = Notification(
                user_id=registration.participant_id,
                event_id=event.id,
                title="Event Reminder",
                message=build_reminder_message(event),
                deduplication_key=key,
            )
            try:
                # The unique constraint also protects against concurrent runs.
                async with db.begin_nested():
                    db.add(notification)
                    await db.flush()
                created += 1
            except IntegrityError:
                continue

    if created:
        await db.commit()
    return created


async def main() -> None:
    async with AsyncSessionLocal() as db:
        count = await send_due_event_reminders(db)
    print(f"Created {count} event reminder(s).")


if __name__ == "__main__":
    asyncio.run(main())
