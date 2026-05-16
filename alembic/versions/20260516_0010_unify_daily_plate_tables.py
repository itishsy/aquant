"""Unify daily plate and related stock tables.

Revision ID: 20260516_0010
Revises: 20260514_0009
Create Date: 2026-05-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260516_0010"
down_revision = "20260514_0009"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str], unique: bool = False) -> None:
    if not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _create_tables() -> None:
    if not _has_table("mkt_daily_plate"):
        op.create_table(
            "mkt_daily_plate",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("plate_type", sa.String(length=32), nullable=False, server_default="limit_up"),
            sa.Column("platform", sa.String(length=32), nullable=False, server_default="cls"),
            sa.Column("rank_no", sa.Integer(), nullable=True),
            sa.Column("plate_code", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("plate_name", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("change_pct", sa.Float(), nullable=True),
            sa.Column("raw_score", sa.Float(), nullable=True),
            sa.Column("limit_up_count", sa.Integer(), nullable=True),
            sa.Column("up_reason", sa.Text(), nullable=False),
            sa.Column("source_update_time", sa.DateTime(), nullable=True),
            sa.Column("collected_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("trade_date", "plate_type", "platform", "plate_code", name="uq_mkt_daily_plate_identity"),
        )
        op.create_index("ix_mkt_daily_plate_trade_date", "mkt_daily_plate", ["trade_date"])
        op.create_index("ix_mkt_daily_plate_plate_type", "mkt_daily_plate", ["plate_type"])
        op.create_index("ix_mkt_daily_plate_platform", "mkt_daily_plate", ["platform"])
        op.create_index("ix_mkt_daily_plate_plate_code", "mkt_daily_plate", ["plate_code"])
        op.create_index("ix_mkt_daily_plate_plate_name", "mkt_daily_plate", ["plate_name"])
    else:
        _create_index_if_missing("ix_mkt_daily_plate_trade_date", "mkt_daily_plate", ["trade_date"])
        _create_index_if_missing("ix_mkt_daily_plate_plate_type", "mkt_daily_plate", ["plate_type"])
        _create_index_if_missing("ix_mkt_daily_plate_platform", "mkt_daily_plate", ["platform"])
        _create_index_if_missing("ix_mkt_daily_plate_plate_code", "mkt_daily_plate", ["plate_code"])
        _create_index_if_missing("ix_mkt_daily_plate_plate_name", "mkt_daily_plate", ["plate_name"])

    if not _has_table("mkt_daily_plate_stock"):
        op.create_table(
            "mkt_daily_plate_stock",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("plate_id", sa.Integer(), nullable=False),
            sa.Column("stock_code", sa.String(length=16), nullable=False),
            sa.Column("stock_name", sa.String(length=64), nullable=False, server_default=""),
            sa.Column("change_pct", sa.Float(), nullable=True),
            sa.Column("last_price", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("plate_id", "stock_code", name="uq_mkt_daily_plate_stock"),
        )
        op.create_index("ix_mkt_daily_plate_stock_plate_id", "mkt_daily_plate_stock", ["plate_id"])
        op.create_index("ix_mkt_daily_plate_stock_stock_code", "mkt_daily_plate_stock", ["stock_code"])
    else:
        _add_column_if_missing("mkt_daily_plate_stock", sa.Column("plate_id", sa.Integer(), nullable=False))
        _add_column_if_missing("mkt_daily_plate_stock", sa.Column("stock_code", sa.String(length=16), nullable=False))
        _add_column_if_missing("mkt_daily_plate_stock", sa.Column("stock_name", sa.String(length=64), nullable=False, server_default=""))
        _add_column_if_missing("mkt_daily_plate_stock", sa.Column("change_pct", sa.Float(), nullable=True))
        _add_column_if_missing("mkt_daily_plate_stock", sa.Column("last_price", sa.Float(), nullable=True))
        _add_column_if_missing("mkt_daily_plate_stock", sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
        _add_column_if_missing("mkt_daily_plate_stock", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
        _create_index_if_missing("ix_mkt_daily_plate_stock_plate_id", "mkt_daily_plate_stock", ["plate_id"])
        _create_index_if_missing("ix_mkt_daily_plate_stock_stock_code", "mkt_daily_plate_stock", ["stock_code"])


def upgrade() -> None:
    _create_tables()


def downgrade() -> None:
    if _has_table("mkt_daily_plate_stock"):
        op.drop_table("mkt_daily_plate_stock")
    if _has_table("mkt_daily_plate"):
        op.drop_table("mkt_daily_plate")
