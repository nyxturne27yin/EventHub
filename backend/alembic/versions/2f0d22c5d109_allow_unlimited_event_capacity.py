"""allow unlimited event capacity

Revision ID: 2f0d22c5d109
Revises: f64c3c709bba
Create Date: 2026-10-20 21:04:06.091278
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f0d22c5d109"
down_revision: Union[str, Sequence[str], None] = "f64c3c709bba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow events to have unlimited capacity."""
    op.alter_column(
        "events",
        "capacity",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    """Require event capacity again."""
    op.alter_column(
        "events",
        "capacity",
        existing_type=sa.Integer(),
        nullable=False,
    )