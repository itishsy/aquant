"""Add missing timestamp columns on unified daily plate tables.

Revision ID: 20260516_0019
Revises: 20260516_0018
Create Date: 2026-05-16
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0019"
down_revision: str | None = "20260516_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _add_timestamp_columns(table_name: str) -> None:
    if not _has_table(table_name):
        return
    columns = _columns(table_name)
    if "created_at" not in columns:
        op.add_column(
            table_name,
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    if "updated_at" not in columns:
        op.add_column(
            table_name,
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )


def upgrade() -> None:
    _add_timestamp_columns("mkt_daily_plate")
    _add_timestamp_columns("mkt_daily_plate_stock")


def downgrade() -> None:
    for table_name in ("mkt_daily_plate_stock", "mkt_daily_plate"):
        if not _has_table(table_name):
            continue
        columns = _columns(table_name)
        if "updated_at" in columns:
            op.drop_column(table_name, "updated_at")
        if "created_at" in columns:
            op.drop_column(table_name, "created_at")
