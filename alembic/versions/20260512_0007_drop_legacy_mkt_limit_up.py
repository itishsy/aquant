"""Drop legacy mkt_limit_up table.

Revision ID: 20260512_0007
Revises: 20260510_0006
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "20260512_0007"
down_revision = "20260510_0006"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if _has_table("mkt_limit_up"):
        op.drop_table("mkt_limit_up")


def downgrade() -> None:
    # Legacy table intentionally not recreated. Use mkt_limit_up_stock instead.
    pass
