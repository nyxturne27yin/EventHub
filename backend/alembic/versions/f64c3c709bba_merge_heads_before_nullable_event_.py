"""merge heads before nullable event capacity

Revision ID: f64c3c709bba
Revises: c3f6a2d91e70, d9f435368a73
Create Date: 2026-10-20 21:02:57.333588

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f64c3c709bba'
down_revision: Union[str, Sequence[str], None] = ('c3f6a2d91e70', 'd9f435368a73')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
