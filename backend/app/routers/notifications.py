from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.dependencies.auth import require_role
from app.models.event import Event
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    result = await db.execute(
        select(Notification, Event)
        .join(Event, Notification.event_id == Event.id)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )

    return [
        {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "event_id": event.id,
            "event_title": event.title,
            "event_date": event.event_date,
            "start_time": event.start_time,
            "mode": event.mode,
            "venue": event.venue,
            "meeting_link": event.meeting_link,
            "is_read": notification.is_read,
            "created_at": notification.created_at,
        }
        for notification, event in result.all()
    ]


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int = Path(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await db.commit()

    return {"id": notification.id, "is_read": notification.is_read}
