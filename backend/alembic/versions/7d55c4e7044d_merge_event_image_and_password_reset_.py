"""merge event image and password reset migrations

Revision ID: 7d55c4e7044d
Revises: 48e726a05df2, ev148_password_reset_rate_limit
Create Date: 2026-11-04 19:24:58.819452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d55c4e7044d'
down_revision: Union[str, Sequence[str], None] = ('48e726a05df2', 'ev148_password_reset_rate_limit')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
