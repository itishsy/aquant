"""Upgrade watch-pool lifecycle schema.

Revision ID: 20260514_0009
Revises: 20260512_0008
Create Date: 2026-05-14 00:09:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260514_0009"
down_revision = "20260512_0008"
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


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    if _has_table(table_name) and not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if _has_index(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def _clear_development_watch_data() -> None:
    # This project is in development and the new lifecycle fields intentionally
    # reset watch/signal/trade/review-trade business records.
    for table_name in [
        "review_trade",
        "watch_trade_execution",
        "watch_signal_performance",
        "watch_trade",
        "watch_signal",
        "watch_pool_status_log",
        "watch_pool",
    ]:
        if _has_table(table_name):
            op.execute(sa.text(f"DELETE FROM {table_name}"))


def upgrade() -> None:
    _clear_development_watch_data()

    _add_column_if_missing("watch_pool", sa.Column("entry_source", sa.String(length=32), nullable=False, server_default="manual"))
    _add_column_if_missing("watch_pool", sa.Column("entry_reason", sa.Text(), nullable=True))
    _add_column_if_missing("watch_pool", sa.Column("trading_system", sa.String(length=32), nullable=True))
    _add_column_if_missing("watch_pool", sa.Column("system_recommendation", sa.String(length=32), nullable=True))
    _add_column_if_missing("watch_pool", sa.Column("lifecycle_status", sa.String(length=32), nullable=False, server_default="watching"))
    _add_column_if_missing("watch_pool", sa.Column("key_observe_price", sa.Float(), nullable=True))
    _add_column_if_missing("watch_pool", sa.Column("invalid_condition", sa.Text(), nullable=True))
    _add_column_if_missing("watch_pool", sa.Column("risk_tags", sa.JSON(), nullable=True))
    _add_column_if_missing("watch_pool", sa.Column("signal_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    _add_column_if_missing("watch_pool", sa.Column("latest_signal_id", sa.Integer(), nullable=True))
    _add_column_if_missing("watch_pool", sa.Column("user_remark", sa.Text(), nullable=True))

    _add_column_if_missing("watch_pool_status_log", sa.Column("operation_type", sa.String(length=32), nullable=False, server_default="status_change"))
    _add_column_if_missing("watch_pool_status_log", sa.Column("snapshot", sa.JSON(), nullable=True))

    _add_column_if_missing("watch_signal", sa.Column("trading_system", sa.String(length=32), nullable=True))
    _add_column_if_missing("watch_signal", sa.Column("buy_point_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing("watch_signal", sa.Column("buy_point_confirm_time", sa.DateTime(), nullable=True))
    _add_column_if_missing("watch_signal", sa.Column("buy_point_confirm_price", sa.Float(), nullable=True))
    _add_column_if_missing("watch_signal", sa.Column("abandoned_flag", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing("watch_signal", sa.Column("abandoned_reason", sa.Text(), nullable=True))
    _add_column_if_missing("watch_signal", sa.Column("abandoned_time", sa.DateTime(), nullable=True))
    _add_column_if_missing("watch_signal", sa.Column("prevent_duplicate_signal", sa.Boolean(), nullable=False, server_default=sa.true()))
    _add_column_if_missing("watch_signal", sa.Column("trigger_signature", sa.String(length=128), nullable=True))

    _add_column_if_missing("watch_trade", sa.Column("trading_system", sa.String(length=32), nullable=True))
    _add_column_if_missing("watch_trade", sa.Column("buy_reason", sa.Text(), nullable=True))
    _add_column_if_missing("watch_trade", sa.Column("trade_plan", sa.Text(), nullable=True))
    _add_column_if_missing("watch_trade", sa.Column("emotion_state", sa.String(length=32), nullable=True))

    _create_index_if_missing("watch_pool", "ix_watch_pool_code_lifecycle", ["stock_code", "lifecycle_status"])
    _create_index_if_missing("watch_pool", "ix_watch_pool_trading_system", ["trading_system"])
    _create_index_if_missing("watch_pool", "ix_watch_pool_latest_signal_id", ["latest_signal_id"])
    _create_index_if_missing("watch_pool_status_log", "ix_watch_pool_status_log_operation_type", ["operation_type"])
    _create_index_if_missing("watch_signal", "ix_watch_signal_watch_status", ["watch_id", "signal_status"])
    _create_index_if_missing("watch_signal", "ix_watch_signal_trigger_signature", ["trigger_signature"])
    _create_index_if_missing("watch_signal", "ix_watch_signal_trading_system", ["trading_system"])
    _create_index_if_missing("watch_signal", "ix_watch_signal_abandoned_flag", ["abandoned_flag"])
    _create_index_if_missing("watch_trade", "ix_watch_trade_watch_status", ["watch_id", "trade_status"])
    _create_index_if_missing("watch_trade", "ix_watch_trade_trading_system", ["trading_system"])


def downgrade() -> None:
    _drop_index_if_exists("watch_trade", "ix_watch_trade_trading_system")
    _drop_index_if_exists("watch_trade", "ix_watch_trade_watch_status")
    _drop_index_if_exists("watch_signal", "ix_watch_signal_abandoned_flag")
    _drop_index_if_exists("watch_signal", "ix_watch_signal_trading_system")
    _drop_index_if_exists("watch_signal", "ix_watch_signal_trigger_signature")
    _drop_index_if_exists("watch_signal", "ix_watch_signal_watch_status")
    _drop_index_if_exists("watch_pool_status_log", "ix_watch_pool_status_log_operation_type")
    _drop_index_if_exists("watch_pool", "ix_watch_pool_latest_signal_id")
    _drop_index_if_exists("watch_pool", "ix_watch_pool_trading_system")
    _drop_index_if_exists("watch_pool", "ix_watch_pool_code_lifecycle")

    for column_name in ["emotion_state", "trade_plan", "buy_reason", "trading_system"]:
        _drop_column_if_exists("watch_trade", column_name)

    for column_name in [
        "trigger_signature",
        "prevent_duplicate_signal",
        "abandoned_time",
        "abandoned_reason",
        "abandoned_flag",
        "buy_point_confirm_price",
        "buy_point_confirm_time",
        "buy_point_confirmed",
        "trading_system",
    ]:
        _drop_column_if_exists("watch_signal", column_name)

    for column_name in ["snapshot", "operation_type"]:
        _drop_column_if_exists("watch_pool_status_log", column_name)

    for column_name in [
        "user_remark",
        "latest_signal_id",
        "signal_enabled",
        "risk_tags",
        "invalid_condition",
        "key_observe_price",
        "lifecycle_status",
        "system_recommendation",
        "trading_system",
        "entry_reason",
        "entry_source",
    ]:
        _drop_column_if_exists("watch_pool", column_name)
