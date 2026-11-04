"""Add event cover image URL.

Revision ID: ev147_event_cover_images
Revises: ev84_event_reminders
"""
from alembic import op
import sqlalchemy as sa

revision = "ev147_event_cover_images"
down_revision = "ev84_event_reminders"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "events",
        sa.Column("cover_image_url", sa.String(length=500), nullable=True),
    )


def downgrade():
    op.drop_column("events", "cover_image_url")
