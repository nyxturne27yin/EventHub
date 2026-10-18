"""create certificates table

Revision ID: b8d2f1a6c903
Revises: 1ef2de084814
"""
from alembic import op
import sqlalchemy as sa

revision = "b8d2f1a6c903"
down_revision = "1ef2de084814"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("certificate_id", sa.String(36), nullable=False, unique=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("student_id", "event_id", name="uq_certificate_student_event"),
    )
    op.create_index("ix_certificates_certificate_id", "certificates", ["certificate_id"])
    op.create_index("ix_certificates_student_id", "certificates", ["student_id"])
    op.create_index("ix_certificates_event_id", "certificates", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_certificates_event_id", table_name="certificates")
    op.drop_index("ix_certificates_student_id", table_name="certificates")
    op.drop_index("ix_certificates_certificate_id", table_name="certificates")
    op.drop_table("certificates")
