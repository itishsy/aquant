"""Add detailed index fields to mkt_daily.

Revision ID: 20260510_0002
Revises: 20260505_0001
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260510_0002"
down_revision = "20260505_0001"
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
    _add_column_if_missing(sa.Column("sh_index_change_pct", sa.Float(), nullable=True))
    _add_column_if_missing(sa.Column("sh_index_change_px", sa.Float(), nullable=True))
    _add_column_if_missing(sa.Column("sz_index_change_pct", sa.Float(), nullable=True))
    _add_column_if_missing(sa.Column("sz_index_change_px", sa.Float(), nullable=True))
    _add_column_if_missing(sa.Column("cyb_index_change_pct", sa.Float(), nullable=True))
    _add_column_if_missing(sa.Column("cyb_index_change_px", sa.Float(), nullable=True))
    _add_column_if_missing(sa.Column("index_trade_status", sa.JSON(), nullable=True))
    _add_column_if_missing(sa.Column("today_chances", sa.JSON(), nullable=True))
    _add_column_if_missing(sa.Column("today_tuyeres", sa.JSON(), nullable=True))
    _add_column_if_missing(sa.Column("topic_list", sa.JSON(), nullable=True))


def downgrade() -> None:
    _drop_column_if_exists("topic_list")
    _drop_column_if_exists("today_tuyeres")
    _drop_column_if_exists("today_chances")
    _drop_column_if_exists("index_trade_status")
    _drop_column_if_exists("cyb_index_change_px")
    _drop_column_if_exists("cyb_index_change_pct")
    _drop_column_if_exists("sz_index_change_px")
    _drop_column_if_exists("sz_index_change_pct")
    _drop_column_if_exists("sh_index_change_px")
    _drop_column_if_exists("sh_index_change_pct")
