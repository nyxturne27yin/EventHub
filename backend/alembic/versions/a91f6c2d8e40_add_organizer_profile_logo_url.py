"""add organizer profile logo url

Revision ID: a91f6c2d8e40
Revises: 7d55c4e7044d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a91f6c2d8e40"
down_revision: Union[str, Sequence[str], None] = "7d55c4e7044d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizer_profiles",
        sa.Column("logo_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizer_profiles", "logo_url")
