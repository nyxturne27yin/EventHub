"""create organizer profiles

Revision ID: 1ef2de084814
Revises: 7a91c4e2d610
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1ef2de084814"
down_revision: Union[str, Sequence[str], None] = "7a91c4e2d610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizer_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("organization_name", sa.String(150), nullable=True),
        sa.Column("department", sa.String(150), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_index(
        "ix_organizer_profiles_user_id",
        "organizer_profiles",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organizer_profiles_user_id",
        table_name="organizer_profiles",
    )
    op.drop_table("organizer_profiles")