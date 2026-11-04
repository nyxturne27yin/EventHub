"""Add per-account password reset request cooldown.

Revision ID: ev148_password_reset_rate_limit
Revises: ev147_event_cover_images
"""
from alembic import op
import sqlalchemy as sa

revision = "ev148_password_reset_rate_limit"
down_revision = "ev147_event_cover_images"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("password_reset_requested_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("users", "password_reset_requested_at")
