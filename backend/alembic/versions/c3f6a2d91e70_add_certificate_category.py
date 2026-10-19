"""Add category to certificates.

Revision ID: c3f6a2d91e70
Revises: b8d2f1a6c903
"""

from alembic import op
import sqlalchemy as sa

revision = "c3f6a2d91e70"
down_revision = "b8d2f1a6c903"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "certificates",
        sa.Column(
            "category",
            sa.String(length=20),
            nullable=False,
            server_default="Academic",
        ),
    )
    op.create_check_constraint(
        "ck_certificates_category",
        "certificates",
        "category IN ('Academic', 'Research')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_certificates_category",
        "certificates",
        type_="check",
    )
    op.drop_column("certificates", "category")
