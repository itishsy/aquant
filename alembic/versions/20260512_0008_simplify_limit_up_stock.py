"""Simplify limit-up storage into stock table.

Revision ID: 20260512_0008
Revises: 20260512_0007
Create Date: 2026-05-12 00:08:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260512_0008"
down_revision = "20260512_0007"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return column_name in {column["name"] for column in _inspector().get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return index_name in {index["name"] for index in _inspector().get_indexes(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if _has_table(table_name) and not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if _has_index(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    _add_column_if_missing(
        "mkt_limit_up_stock",
        sa.Column("raw_secu_code", sa.String(length=32), nullable=False, server_default=""),
    )
    _add_column_if_missing("mkt_limit_up_stock", sa.Column("limit_datetime", sa.DateTime(), nullable=True))
    _add_column_if_missing("mkt_limit_up_stock", sa.Column("board_days", sa.Integer(), nullable=True))

    if _has_table("mkt_limit_up_stock"):
        if not _has_index("mkt_limit_up_stock", "ix_mkt_limit_up_stock_raw_secu_code"):
            op.create_index("ix_mkt_limit_up_stock_raw_secu_code", "mkt_limit_up_stock", ["raw_secu_code"])
        if not _has_index("mkt_limit_up_stock", "ix_mkt_limit_up_stock_limit_datetime"):
            op.create_index("ix_mkt_limit_up_stock_limit_datetime", "mkt_limit_up_stock", ["limit_datetime"])

    if _has_table("mkt_limit_up_ladder_stock"):
        op.drop_table("mkt_limit_up_ladder_stock")
    if _has_table("mkt_limit_up_ladder"):
        op.drop_table("mkt_limit_up_ladder")


def downgrade() -> None:
    if _has_table("mkt_limit_up_stock"):
        _drop_index_if_exists("mkt_limit_up_stock", "ix_mkt_limit_up_stock_limit_datetime")
        _drop_index_if_exists("mkt_limit_up_stock", "ix_mkt_limit_up_stock_raw_secu_code")
        if _has_column("mkt_limit_up_stock", "board_days"):
            op.drop_column("mkt_limit_up_stock", "board_days")
        if _has_column("mkt_limit_up_stock", "limit_datetime"):
            op.drop_column("mkt_limit_up_stock", "limit_datetime")
        if _has_column("mkt_limit_up_stock", "raw_secu_code"):
            op.drop_column("mkt_limit_up_stock", "raw_secu_code")
