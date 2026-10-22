"""Add reminder idempotency key.

Revision ID: ev84_event_reminders
"""
from alembic import op
import sqlalchemy as sa

revision = "ev84_event_reminders"
down_revision = ('2f0d22c5d109', 'ev79_notification_history')
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "notifications",
        sa.Column("deduplication_key", sa.String(length=200), nullable=True),
    )
    op.create_unique_constraint(
        "uq_notifications_deduplication_key",
        "notifications",
        ["deduplication_key"],
    )


def downgrade():
    op.drop_constraint(
        "uq_notifications_deduplication_key",
        "notifications",
        type_="unique",
    )
    op.drop_column("notifications", "deduplication_key")
