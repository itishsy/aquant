"""Add limit-up ladder JSON field to mkt_daily.

Revision ID: 20260510_0004
Revises: 20260510_0003
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260510_0004"
down_revision = "20260510_0003"
branch_labels = None
depends_on = None


TABLE_NAME = "mkt_daily"


def _has_column(column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def upgrade() -> None:
    if not _has_column("limit_up_ladder"):
        op.add_column(TABLE_NAME, sa.Column("limit_up_ladder", sa.JSON(), nullable=True))


def downgrade() -> None:
    if _has_column("limit_up_ladder"):
        op.drop_column(TABLE_NAME, "limit_up_ladder")
