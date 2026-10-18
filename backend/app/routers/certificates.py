import os
import uuid
from io import BytesIO
from uuid import UUID

import qrcode
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.certificate import Certificate
from app.models.event import Event
from app.models.user import User

router = APIRouter(prefix="/certificates", tags=["Certificates"])


class CertificateGenerateRequest(BaseModel):
    student_id: int = Field(gt=0)


@router.post("/events/{event_id}/generate", status_code=201)
async def generate_certificate(
    event_id: int,
    payload: CertificateGenerateRequest,
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
            detail="You can only issue certificates for your own events",
        )

    if (event.status or "").strip().lower() != "completed":
        raise HTTPException(
            status_code=409,
            detail="Certificates can only be issued for completed events",
        )

    result = await db.execute(select(User).where(User.id == payload.student_id))
    student = result.scalar_one_or_none()

    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.role is None or student.role.name.strip().lower() != "student":
        raise HTTPException(
            status_code=400,
            detail="Certificates can only be issued to student accounts",
        )

    result = await db.execute(
        select(Certificate).where(
            Certificate.student_id == student.id,
            Certificate.event_id == event.id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail="Certificate already issued for this student and event",
        )

    certificate = Certificate(student_id=student.id, event_id=event.id)
    db.add(certificate)

    try:
        await db.commit()
        await db.refresh(certificate)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Certificate already issued for this student and event",
        )

    return {
        "message": "Certificate generated successfully",
        "certificate": {
            "certificate_id": certificate.certificate_id,
            "student_id": certificate.student_id,
            "event_id": event.id,
            "event_title": event.title,
            "issued_at": certificate.issued_at,
            "verification_path": f"/certificates/verify/{certificate.certificate_id}",
            "qr_path": f"/certificates/verify/{certificate.certificate_id}/qr",
        },
    }


@router.get("/me")
async def my_certificates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Certificate, Event)
        .join(Event, Certificate.event_id == Event.id)
        .where(Certificate.student_id == current_user.id)
        .order_by(Certificate.issued_at.desc())
    )

    return [
        {
            "certificate_id": cert.certificate_id,
            "event_id": event.id,
            "event_title": event.title,
            "issued_at": cert.issued_at,
            "verification_path": f"/certificates/verify/{cert.certificate_id}",
            "qr_path": f"/certificates/verify/{cert.certificate_id}/qr",
        }
        for cert, event in result.all()
    ]


@router.get("/verify/{certificate_id}")
async def verify_certificate(
    certificate_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        parsed_id = str(UUID(certificate_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="Certificate not found")

    result = await db.execute(
        select(Certificate).where(Certificate.certificate_id == parsed_id)
    )
    cert = result.scalar_one_or_none()

    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")

    result = await db.execute(select(Event).where(Event.id == cert.event_id))
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(status_code=404, detail="Certificate event not found")

    result = await db.execute(select(User).where(User.id == cert.student_id))
    student = result.scalar_one_or_none()

    return {
        "valid": True,
        "certificate_id": cert.certificate_id,
        "student_name": student.name if student else None,
        "event_title": event.title,
        "issued_at": cert.issued_at,
    }


@router.get("/verify/{certificate_id}/qr")
async def certificate_qr(
    certificate_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        parsed_id = str(UUID(certificate_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="Certificate not found")

    result = await db.execute(
        select(Certificate).where(Certificate.certificate_id == parsed_id)
    )
    cert = result.scalar_one_or_none()

    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")

    base_url = os.getenv("PUBLIC_API_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(
            status_code=503,
            detail="PUBLIC_API_BASE_URL is not configured",
        )

    verify_url = f"{base_url}/certificates/verify/{cert.certificate_id}"
    qr = qrcode.make(verify_url)
    image_buffer = BytesIO()
    qr.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    return StreamingResponse(image_buffer, media_type="image/png")
