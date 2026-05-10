"""Optimize limit-up analysis tables.

Revision ID: 20260510_0006
Revises: 20260510_0005
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260510_0006"
down_revision = "20260510_0005"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    if not _has_table("mkt_limit_up_plate"):
        op.create_table(
            "mkt_limit_up_plate",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("plate_code", sa.String(length=32), nullable=False),
            sa.Column("plate_name", sa.String(length=128), nullable=False),
            sa.Column("change_pct", sa.Float(), nullable=True),
            sa.Column("limit_up_count", sa.Integer(), nullable=True),
            sa.Column("up_reason", sa.Text(), nullable=False),
            sa.Column("source_update_time", sa.DateTime(), nullable=True),
            sa.Column("collected_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("trade_date", "source", "plate_code", name="uq_mkt_limit_plate_day_source_code"),
        )
        op.create_index("ix_mkt_limit_up_plate_trade_date", "mkt_limit_up_plate", ["trade_date"])
        op.create_index("ix_mkt_limit_up_plate_source", "mkt_limit_up_plate", ["source"])
        op.create_index("ix_mkt_limit_up_plate_platform", "mkt_limit_up_plate", ["platform"])
        op.create_index("ix_mkt_limit_up_plate_plate_code", "mkt_limit_up_plate", ["plate_code"])
        op.create_index("ix_mkt_limit_up_plate_plate_name", "mkt_limit_up_plate", ["plate_name"])

    if not _has_table("mkt_limit_up_stock"):
        op.create_table(
            "mkt_limit_up_stock",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("stock_code", sa.String(length=16), nullable=False),
            sa.Column("stock_name", sa.String(length=64), nullable=False),
            sa.Column("plate_code", sa.String(length=32), nullable=False),
            sa.Column("plate_name", sa.String(length=128), nullable=False),
            sa.Column("change_pct", sa.Float(), nullable=True),
            sa.Column("last_price", sa.Float(), nullable=True),
            sa.Column("circulating_market_cap", sa.Float(), nullable=True),
            sa.Column("limit_time", sa.String(length=32), nullable=True),
            sa.Column("board_count", sa.Integer(), nullable=True),
            sa.Column("board_text", sa.String(length=64), nullable=False),
            sa.Column("limit_reason", sa.Text(), nullable=False),
            sa.Column("reason_tags", sa.String(length=256), nullable=False),
            sa.Column("ladder_height", sa.Integer(), nullable=True),
            sa.Column("source_update_time", sa.DateTime(), nullable=True),
            sa.Column("collected_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("trade_date", "source", "stock_code", name="uq_mkt_limit_stock_day_source_code"),
        )
        op.create_index("ix_mkt_limit_up_stock_trade_date", "mkt_limit_up_stock", ["trade_date"])
        op.create_index("ix_mkt_limit_up_stock_source", "mkt_limit_up_stock", ["source"])
        op.create_index("ix_mkt_limit_up_stock_platform", "mkt_limit_up_stock", ["platform"])
        op.create_index("ix_mkt_limit_up_stock_stock_code", "mkt_limit_up_stock", ["stock_code"])
        op.create_index("ix_mkt_limit_up_stock_plate_code", "mkt_limit_up_stock", ["plate_code"])
        op.create_index("ix_mkt_limit_up_stock_plate_name", "mkt_limit_up_stock", ["plate_name"])
        op.create_index("ix_mkt_limit_up_stock_ladder_height", "mkt_limit_up_stock", ["ladder_height"])

    if _has_table("mkt_limit_up_ladder"):
        _add_column_if_missing("mkt_limit_up_ladder", sa.Column("platform", sa.String(length=32), nullable=False, server_default="cls"))


def downgrade() -> None:
    if _has_table("mkt_limit_up_stock"):
        op.drop_table("mkt_limit_up_stock")
    if _has_table("mkt_limit_up_plate"):
        op.drop_table("mkt_limit_up_plate")
