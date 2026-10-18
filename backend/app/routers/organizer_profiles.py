
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.event import Event
from app.models.organizer_profile import OrganizerProfile
from app.models.role import Role
from app.models.user import User
from app.schemas.organizer_profile import OrganizerProfileUpdate


router = APIRouter(
    prefix="/organizer-profiles",
    tags=["Organizer Profiles"],
)


def profile_response(profile: OrganizerProfile) -> dict:
    return {
        "user_id": profile.user_id,
        "name": profile.user.name,
        "organization_name": profile.organization_name,
        "department": profile.department,
        "bio": profile.bio,
        "contact_phone": profile.contact_phone,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


@router.get("/me")
async def get_my_organizer_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("organizer")),
):
    result = await db.execute(
        select(OrganizerProfile)
        .options(selectinload(OrganizerProfile.user))
        .where(OrganizerProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return {
            "user_id": current_user.id,
            "name": current_user.name,
            "organization_name": None,
            "department": None,
            "bio": None,
            "contact_phone": None,
        }

    return profile_response(profile)


@router.put("/me")
async def update_my_organizer_profile(
    payload: OrganizerProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("organizer")),
):
    result = await db.execute(
        select(OrganizerProfile).where(
            OrganizerProfile.user_id == current_user.id
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = OrganizerProfile(user_id=current_user.id)
        db.add(profile)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    profile.updated_at = datetime.now(UTC).replace(tzinfo=None)

    await db.commit()

    result = await db.execute(
        select(OrganizerProfile)
        .options(selectinload(OrganizerProfile.user))
        .where(OrganizerProfile.user_id == current_user.id)
    )
    profile = result.scalar_one()

    return profile_response(profile)


@router.get("/{user_id}")
async def get_organizer_profile(
    user_id: int = Path(gt=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(OrganizerProfile)
        .join(User, OrganizerProfile.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .options(selectinload(OrganizerProfile.user))
        .where(
            OrganizerProfile.user_id == user_id,
            Role.name.ilike("organizer"),
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organizer profile not found",
        )

    events_result = await db.execute(
        select(Event)
        .where(
            Event.organizer_id == user_id,
            Event.status == "published",
        )
        .order_by(Event.event_date, Event.start_time)
    )
    events = events_result.scalars().all()

    response = profile_response(profile)
    response["events"] = [
        {
            "id": event.id,
            "title": event.title,
            "event_date": event.event_date,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "mode": event.mode,
            "venue": event.venue,
        }
        for event in events
    ]

    return response
