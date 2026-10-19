"""add event registration status

Revision ID: d9f435368a73
Revises: b8d2f1a6c903
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d9f435368a73"
down_revision: Union[str, Sequence[str], None] = "b8d2f1a6c903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_registrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "participant_id",
            name="uq_event_registration_participant",
        ),
    )
    op.create_index(
        "ix_event_registrations_event_id",
        "event_registrations",
        ["event_id"],
        unique=False,
    )
    op.create_index(
        "ix_event_registrations_participant_id",
        "event_registrations",
        ["participant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_event_registrations_participant_id",
        table_name="event_registrations",
    )
    op.drop_index(
        "ix_event_registrations_event_id",
        table_name="event_registrations",
    )
    op.drop_table("event_registrations")
