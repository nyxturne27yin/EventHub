from datetime import UTC, datetime
import logging
import uuid

from fastapi import File, UploadFile

from app.core.image_validation import (
    ALLOWED_IMAGE_FORMATS,
    MAX_COVER_IMAGE_BYTES,
    inspect_cover_image,
)
from app.core.storage import (
    CLUB_LOGO_IMAGE_DIR,
    resolve_club_logo_path,
)

logger = logging.getLogger(__name__)

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
        "logo_url": profile.logo_url,
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
            "logo_url": None,
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

@router.post("/me/logo")
async def upload_club_logo(
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("organizer")),
):
    """Upload or replace the current organizer's club logo."""
    content = await image.read(MAX_COVER_IMAGE_BYTES + 1)
    await image.close()

    try:
        image_format, _, _ = inspect_cover_image(content)
    except ValueError as error:
        code = 413 if len(content) > MAX_COVER_IMAGE_BYTES else 400
        raise HTTPException(status_code=code, detail=str(error)) from error

    result = await db.execute(
        select(OrganizerProfile).where(
            OrganizerProfile.user_id == current_user.id
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = OrganizerProfile(
            user_id=current_user.id,
            organization_name=current_user.name,
        )
        db.add(profile)
        await db.flush()

    filename = f"{uuid.uuid4().hex}{ALLOWED_IMAGE_FORMATS[image_format]}"
    destination = CLUB_LOGO_IMAGE_DIR / filename

    try:
        destination.write_bytes(content)
        previous_path = resolve_club_logo_path(profile.logo_url)
        profile.logo_url = f"/uploads/club-logos/{filename}"
        profile.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()
    except Exception as error:
        destination.unlink(missing_ok=True)
        await db.rollback()
        logger.exception("Could not save club logo")
        raise HTTPException(
            status_code=500,
            detail="Could not save the club logo.",
        ) from error

    if previous_path and previous_path != destination:
        try:
            previous_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove replaced club logo: %s", previous_path)

    return {
        "message": "Club logo uploaded successfully.",
        "logo_url": profile.logo_url,
    }


@router.delete("/me/logo")
async def remove_club_logo(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("organizer")),
):
    """Remove the current organizer's club logo."""
    result = await db.execute(
        select(OrganizerProfile).where(
            OrganizerProfile.user_id == current_user.id
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None or not profile.logo_url:
        raise HTTPException(status_code=404, detail="No club logo was found.")

    previous_path = resolve_club_logo_path(profile.logo_url)
    profile.logo_url = None
    profile.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()

    if previous_path:
        try:
            previous_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove club logo: %s", previous_path)

    return {"message": "Club logo removed successfully."}


@router.get("/clubs")
async def list_public_clubs(
    db: AsyncSession = Depends(get_db),
):
    """List organizer profiles that have a public club name."""
    result = await db.execute(
        select(OrganizerProfile)
        .join(User, OrganizerProfile.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .options(selectinload(OrganizerProfile.user))
        .where(
            Role.name.ilike("organizer"),
            OrganizerProfile.organization_name.is_not(None),
        )
        .order_by(OrganizerProfile.organization_name)
    )

    profiles = result.scalars().all()

    return [
        {
            "user_id": profile.user_id,
            "name": profile.user.name,
            "organization_name": profile.organization_name,
            "department": profile.department,
            "bio": profile.bio,
            "logo_url": profile.logo_url,
        }
        for profile in profiles
    ]


@router.get("/clubs/{user_id}")
async def get_public_club_profile(
    user_id: int = Path(gt=0),
    db: AsyncSession = Depends(get_db),
):
    """Return public club information and its published events."""
    result = await db.execute(
        select(OrganizerProfile)
        .join(User, OrganizerProfile.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .options(selectinload(OrganizerProfile.user))
        .where(
            OrganizerProfile.user_id == user_id,
            Role.name.ilike("organizer"),
            OrganizerProfile.organization_name.is_not(None),
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(status_code=404, detail="Club not found.")

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
            "description": event.description,
            "category": event.category,
            "event_date": event.event_date,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "mode": event.mode,
            "venue": event.venue,
            "cover_image_url": getattr(event, "cover_image_url", None),
        }
        for event in events
    ]
    return response

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

    event_statement = select(Event).where(Event.organizer_id == user_id)

    if current_user.id != user_id:
        event_statement = event_statement.where(
            Event.status.in_(("published", "cancelled", "completed"))
        )

    events_result = await db.execute(
        event_statement.order_by(Event.event_date, Event.start_time)
    )
    events = events_result.scalars().all()

    response = profile_response(profile)
    response["events"] = [
        {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "category": event.category,
            "event_date": event.event_date,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "mode": event.mode,
            "venue": event.venue,
            "cover_image_url": getattr(event, "cover_image_url", None),
            "capacity": event.capacity,
            "registration_deadline": event.registration_deadline,
            "status": event.status,
        }
        for event in events
    ]

    return response