"""add organizer and administrator roles

Revision ID: 7a91c4e2d610
Revises: 0fe4c7b95e0e
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a91c4e2d610"
down_revision: Union[str, Sequence[str], None] = "0fe4c7b95e0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for role_name in ("organizer", "administrator"):
        op.execute(
            sa.text(
                "INSERT INTO roles (name) "
                "SELECT :role_name "
                "WHERE NOT EXISTS "
                "(SELECT 1 FROM roles WHERE name = :role_name)"
            ).bindparams(role_name=role_name)
        )


def downgrade() -> None:
    # Intentionally retain role records: they may have existed before this
    # migration or may have been assigned to users after it was applied.
    pass
