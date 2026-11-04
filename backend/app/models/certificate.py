
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Certificate(Base):
    __tablename__ = "certificates"

    __table_args__ = (
        UniqueConstraint(
            "certificate_id",
            name="certificates_certificate_id_key",
        ),
        UniqueConstraint(
            "student_id",
            "event_id",
            name="uq_certificate_student_event",
        ),
        CheckConstraint(
            "category IN ('Academic', 'Research')",
            name="ck_certificates_category",
        ),
        Index("ix_certificates_certificate_id", "certificate_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    certificate_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        default=lambda: str(uuid.uuid4()),
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id"),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="Academic",
        server_default="Academic",
    )

    issued_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    student = relationship("User")
    event = relationship("Event")
