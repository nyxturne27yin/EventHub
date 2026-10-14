from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.dependencies.auth import require_role
from app.models.event import Event
from app.models.user import User
from app.schemas.event import (
    EventCreateRequest,
    EventSearchItem,
    EventUpdateRequest,
)

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("organizer")),
):
    if (
        current_user.role is None
        or current_user.role.name.lower() != "organizer"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizers can create events",
        )

    event = Event(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        event_date=payload.event_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        mode=payload.mode,
        venue=payload.venue or None,
        meeting_link=payload.meeting_link or None,
        capacity=payload.capacity,
        registration_deadline=payload.registration_deadline,
        status=payload.status,
        organizer_id=current_user.id,
    )

    db.add(event)
    await db.commit()
    await db.refresh(event)

    return {
        "message": "Event created successfully",
        "event": {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "category": event.category,
            "event_date": event.event_date,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "mode": event.mode,
            "venue": event.venue,
            "meeting_link": event.meeting_link,
            "capacity": event.capacity,
            "registration_deadline": event.registration_deadline,
            "status": event.status,
            "organizer_id": event.organizer_id,
        },
    }


@router.get("/", response_model=list[EventSearchItem])
async def list_events(
    search: str | None = Query(default=None, max_length=100),
    db: AsyncSession = Depends(get_db),
):
    statement = select(Event).where(Event.status == "published")
    search_text = search.strip() if search else ""

    if search_text:
        statement = statement.where(
            or_(
                Event.title.icontains(search_text, autoescape=True),
                Event.description.icontains(search_text, autoescape=True),
                Event.category.icontains(search_text, autoescape=True),
            )
        )

    statement = statement.order_by(
        Event.event_date,
        Event.start_time,
        Event.id,
    )

    result = await db.execute(statement)
    return result.scalars().all()


@router.patch("/{event_id}")
async def update_event(
    payload: EventUpdateRequest,
    event_id: int = Path(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("organizer")),
):
    if (
        current_user.role is None
        or current_user.role.name.lower() != "organizer"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizers can update events",
        )

    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    if event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own events",
        )

    if event.status.lower() == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancelled events cannot be updated",
        )

    changes = payload.model_dump(exclude_unset=True)

    values = {
        "title": event.title,
        "description": event.description,
        "category": event.category,
        "event_date": event.event_date,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "mode": event.mode,
        "venue": event.venue,
        "meeting_link": event.meeting_link,
        "capacity": event.capacity,
        "registration_deadline": event.registration_deadline,
    }
    values.update(changes)

    for field in ("title", "description", "category"):
        value = values[field]

        if value is None or not value.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field} cannot be empty",
            )

    if "event_date" in changes and values["event_date"] < date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Event date cannot be in the past",
        )

    if (
        "start_time" in changes or "end_time" in changes
    ) and values["end_time"] <= values["start_time"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="End time must be after start time",
        )

    event_start = datetime.combine(
        values["event_date"],
        values["start_time"],
    )
    deadline = values["registration_deadline"]

    if deadline is None or deadline.tzinfo is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Registration deadline must be a valid local date and time",
        )

    if (
        "event_date" in changes
        or "start_time" in changes
        or "registration_deadline" in changes
    ) and deadline >= event_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Registration deadline must be before the event starts",
        )

    if values["mode"] == "Offline":
        if not values["venue"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Venue is required for offline events",
            )
    elif values["mode"] == "Online":
        if not values["meeting_link"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Meeting link is required for online events",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Mode must be Online or Offline",
        )

    for field, value in changes.items():
        setattr(event, field, value)

    event.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(event)

    return {
        "message": "Event updated successfully",
        "event": {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "category": event.category,
            "event_date": event.event_date,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "mode": event.mode,
            "venue": event.venue,
            "meeting_link": event.meeting_link,
            "capacity": event.capacity,
            "registration_deadline": event.registration_deadline,
            "status": event.status,
            "organizer_id": event.organizer_id,
            "updated_at": event.updated_at,
        },
    }


@router.post("/{event_id}/cancel")
async def cancel_event(
    event_id: int = Path(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("organizer")),
):
    if (
        current_user.role is None
        or current_user.role.name.lower() != "organizer"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizers can cancel events",
        )

    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    if event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own events",
        )

    if event.status.lower() == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event is already cancelled",
        )

    event.status = "cancelled"
    event.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(event)

    return {
        "message": "Event cancelled successfully",
        "event_id": event.id,
        "status": event.status,
    }
