"""add watch pool trading system instance params

Revision ID: 20260523_watchsys
Revises: 20260523_trading_sys
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260523_watchsys"
down_revision: Union[str, None] = "20260523_trading_sys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table_name: str, column_name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def upgrade() -> None:
    with op.batch_alter_table("watch_pool") as batch:
        if not _column_exists("watch_pool", "trading_system_code"):
            batch.add_column(sa.Column("trading_system_code", sa.String(length=64), nullable=True))
        if not _column_exists("watch_pool", "system_stage"):
            batch.add_column(sa.Column("system_stage", sa.String(length=32), nullable=False, server_default="observe"))
        if not _column_exists("watch_pool", "system_params_json"):
            batch.add_column(sa.Column("system_params_json", sa.JSON(), nullable=True))
        if not _column_exists("watch_pool", "active_rule_codes_json"):
            batch.add_column(sa.Column("active_rule_codes_json", sa.JSON(), nullable=True))
        if not _column_exists("watch_pool", "next_action"):
            batch.add_column(sa.Column("next_action", sa.Text(), nullable=True))

    op.execute("update watch_pool set system_stage = 'observe' where system_stage is null or system_stage = ''")

    if not _index_exists("watch_pool", "ix_watch_pool_trading_system_code"):
        op.create_index("ix_watch_pool_trading_system_code", "watch_pool", ["trading_system_code"], unique=False)
    if not _index_exists("watch_pool", "ix_watch_pool_system_stage"):
        op.create_index("ix_watch_pool_system_stage", "watch_pool", ["system_stage"], unique=False)


def downgrade() -> None:
    if _index_exists("watch_pool", "ix_watch_pool_system_stage"):
        op.drop_index("ix_watch_pool_system_stage", table_name="watch_pool")
    if _index_exists("watch_pool", "ix_watch_pool_trading_system_code"):
        op.drop_index("ix_watch_pool_trading_system_code", table_name="watch_pool")

    with op.batch_alter_table("watch_pool") as batch:
        for column_name in [
            "next_action",
            "active_rule_codes_json",
            "system_params_json",
            "system_stage",
            "trading_system_code",
        ]:
            if _column_exists("watch_pool", column_name):
                batch.drop_column(column_name)
