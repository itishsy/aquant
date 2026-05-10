"""Add market subject JSON fields to mkt_daily.

Revision ID: 20260510_0003
Revises: 20260510_0002
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260510_0003"
down_revision = "20260510_0002"
branch_labels = None
depends_on = None


TABLE_NAME = "mkt_daily"


def _has_column(column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def _add_column_if_missing(column: sa.Column) -> None:
    if not _has_column(column.name):
        op.add_column(TABLE_NAME, column)


def _drop_column_if_exists(column_name: str) -> None:
    if _has_column(column_name):
        op.drop_column(TABLE_NAME, column_name)


def upgrade() -> None:
    _add_column_if_missing(sa.Column("today_chances", sa.JSON(), nullable=True))
    _add_column_if_missing(sa.Column("today_tuyeres", sa.JSON(), nullable=True))
    _add_column_if_missing(sa.Column("topic_list", sa.JSON(), nullable=True))


def downgrade() -> None:
    _drop_column_if_exists("topic_list")
    _drop_column_if_exists("today_tuyeres")
    _drop_column_if_exists("today_chances")
