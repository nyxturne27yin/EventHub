from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.dependencies.auth import require_role
from app.models.event import Event
from app.models.registration import EventRegistration
from app.models.user import User
from app.schemas.registration import RegistrationStatusUpdate
from app.services.event_lifecycle import complete_event_if_due

router = APIRouter(tags=["Event Registrations"])


@router.post(
    "/events/{event_id}/registrations",
    status_code=status.HTTP_201_CREATED,
)
async def register_for_event(
    event_id: int = Path(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    result = await db.execute(
        select(Event).where(Event.id == event_id).with_for_update()
    )
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    await complete_event_if_due(db, event)

    event_status = (event.status or "").strip().lower()

    if event_status == "completed":
        raise HTTPException(
            status_code=409,
            detail="Registration is closed because this event is completed",
        )

    if event_status == "cancelled":
        raise HTTPException(
            status_code=409,
            detail="Registration is closed because this event is cancelled",
        )

    if event_status != "published":
        raise HTTPException(status_code=404, detail="Published event not found")

    now = datetime.now()
    event_start = datetime.combine(event.event_date, event.start_time)

    if event.registration_deadline <= now:
        raise HTTPException(
            status_code=409,
            detail="Registration deadline has passed",
        )

    if event_start <= now:
        raise HTTPException(
            status_code=409,
            detail="Event has already started",
        )

    existing = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.participant_id == current_user.id,
        )
    )
    registration = existing.scalar_one_or_none()

    if registration is not None:
        if registration.status == "Cancelled":
            count_result = await db.execute(
                select(func.count(EventRegistration.id)).where(
                    EventRegistration.event_id == event_id,
                    EventRegistration.status == "Registered",
                )
            )
            registered_count = count_result.scalar_one()

            if (
                event.capacity is not None
                and registered_count >= event.capacity
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Event capacity is full",
                )

            raise HTTPException(
                status_code=409,
                detail="Cancelled registration cannot be reactivated",
            )

        raise HTTPException(
            status_code=409,
            detail="Already registered for this event",
        )

    count_result = await db.execute(
        select(func.count(EventRegistration.id)).where(
            EventRegistration.event_id == event_id,
            EventRegistration.status == "Registered",
        )
    )
    registered_count = count_result.scalar_one()

    if event.capacity is not None and registered_count >= event.capacity:
        raise HTTPException(
            status_code=409,
            detail="Event capacity is full",
        )

    registration = EventRegistration(
        event_id=event_id,
        participant_id=current_user.id,
        status="Registered",
    )
    db.add(registration)
    await db.commit()
    await db.refresh(registration)

    return {
        "id": registration.id,
        "event_id": registration.event_id,
        "participant_id": registration.participant_id,
        "status": registration.status,
    }


@router.post("/events/{event_id}/registrations/{registration_id}/cancel")
async def cancel_registration(
    event_id: int = Path(gt=0),
    registration_id: int = Path(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    event_result = await db.execute(
        select(Event).where(Event.id == event_id).with_for_update()
    )
    event = event_result.scalar_one_or_none()

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    # Apply EV-110 lifecycle rules before allowing cancellation.
    await complete_event_if_due(db, event)

    event_status = (event.status or "").strip().lower()

    if event_status == "cancelled":
        raise HTTPException(
            status_code=409,
            detail="Cannot cancel registration for a cancelled event",
        )

    if event_status == "completed":
        raise HTTPException(
            status_code=409,
            detail="Cannot cancel registration after the event has ended",
        )

    event_end = datetime.combine(event.event_date, event.end_time)

    if event_end <= datetime.now():
        raise HTTPException(
            status_code=409,
            detail="Cannot cancel registration after the event has ended",
        )

    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.id == registration_id,
            EventRegistration.event_id == event_id,
        )
    )
    registration = result.scalar_one_or_none()

    if registration is None:
        raise HTTPException(
            status_code=404,
            detail="Registration not found",
        )

    if registration.participant_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only cancel your own registration",
        )

    if registration.status == "Cancelled":
        raise HTTPException(
            status_code=409,
            detail="Registration is already cancelled",
        )

    registration.status = "Cancelled"

    await db.commit()
    await db.refresh(registration)

    return {
        "message": "Registration cancelled successfully",
        "registration_id": registration.id,
        "event_id": registration.event_id,
        "status": registration.status,
    }


@router.get("/events/{event_id}/participants")
async def list_event_participants(
    event_id: int = Path(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("organizer")),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only view participants for your own events",
        )

    await complete_event_if_due(db, event)

    result = await db.execute(
        select(EventRegistration, User)
        .join(User, User.id == EventRegistration.participant_id)
        .where(EventRegistration.event_id == event_id)
        .order_by(EventRegistration.created_at, EventRegistration.id)
    )

    return [
        {
            "id": registration.id,
            "participant_id": participant.id,
            "participant_name": participant.name,
            "participant_email": participant.email,
            "status": registration.status,
            "created_at": registration.created_at,
        }
        for registration, participant in result.all()
    ]


@router.patch("/events/{event_id}/registrations/{registration_id}/status")
async def update_registration_status(
    payload: RegistrationStatusUpdate,
    event_id: int = Path(gt=0),
    registration_id: int = Path(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("organizer")),
):
    result = await db.execute(
        select(Event).where(Event.id == event_id).with_for_update()
    )
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only manage participants for your own events",
        )

    await complete_event_if_due(db, event)

    if (event.status or "").strip().lower() in {"completed", "cancelled"}:
        raise HTTPException(
            status_code=409,
            detail=(
                "Registration statuses cannot be changed for completed "
                "or cancelled events"
            ),
        )

    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.id == registration_id,
            EventRegistration.event_id == event_id,
        )
    )
    registration = result.scalar_one_or_none()

    if registration is None:
        raise HTTPException(
            status_code=404,
            detail="Registration not found",
        )

    registration.status = payload.status

    await db.commit()
    await db.refresh(registration)

    return {
        "id": registration.id,
        "event_id": registration.event_id,
        "participant_id": registration.participant_id,
        "status": registration.status,
    }