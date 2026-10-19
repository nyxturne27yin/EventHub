from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.database import get_db
from app.dependencies.auth import require_role
from app.models.event import Event
from app.models.role import Role
from app.models.user import User


router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(require_role("administrator"))],
)


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["student", "organizer", "administrator"] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_an_update(self):
        if self.role is None and self.is_active is None:
            raise ValueError("Provide a role or account status to update.")
        return self


class EventStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["draft", "published", "cancelled", "completed"]


@router.get("/dashboard")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    total_users = await db.scalar(select(func.count()).select_from(User))
    active_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    )
    total_events = await db.scalar(select(func.count()).select_from(Event))

    role_result = await db.execute(
        select(Role.name, func.count(User.id))
        .outerjoin(User, User.role_id == Role.id)
        .group_by(Role.name)
    )
    status_result = await db.execute(
        select(Event.status, func.count(Event.id)).group_by(Event.status)
    )

    return {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "inactive_users": (total_users or 0) - (active_users or 0),
        "total_events": total_events or 0,
        "users_by_role": {role: count for role, count in role_result.all()},
        "events_by_status": {event_status: count for event_status, count in status_result.all()},
    }


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).options(selectinload(User.role)).order_by(User.id)
    )
    return [
        {"id": user.id, "name": user.name, "email": user.email, "role": user.role.name if user.role else None, "is_active": user.is_active, "created_at": user.created_at}
        for user in result.scalars().all()
    ]


@router.patch("/users/{user_id}")
async def update_user(
    payload: UserUpdateRequest, user_id: int = Path(gt=0),
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_role("administrator")),
):
    result = await db.execute(select(User).options(selectinload(User.role)).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        if payload.role is not None and payload.role != "administrator":
            raise HTTPException(400, "You cannot remove your own administrator role.")
        if payload.is_active is False:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    if payload.role is not None:
        role_result = await db.execute(select(Role).where(Role.name == payload.role))
        role = role_result.scalar_one_or_none()
        if role is None:
            raise HTTPException(status_code=500, detail="Required role is not configured.")
        user.role = role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return {"message": "User updated successfully", "id": user.id, "name": user.name, "role": user.role.name if user.role else None, "is_active": user.is_active}


@router.get("/events")
async def list_all_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).options(selectinload(Event.organizer)).order_by(Event.id.desc()))
    return [
        {"id": event.id, "title": event.title, "event_date": event.event_date, "status": event.status, "organizer_id": event.organizer_id, "organizer_name": event.organizer.name if event.organizer else None}
        for event in result.scalars().all()
    ]


@router.patch("/events/{event_id}/status")
async def update_event_status(payload: EventStatusUpdateRequest, event_id: int = Path(gt=0), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    event.status = payload.status
    await db.commit()
    await db.refresh(event)
    return {"message": "Event status updated successfully", "event_id": event.id, "status": event.status}




