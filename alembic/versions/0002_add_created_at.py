"""add created_at to transactions

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-20
"""

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transactions", "created_at")
