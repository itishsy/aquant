from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260524_signal_rules"
down_revision = "20260523_watchsys"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    with op.batch_alter_table("watch_signal") as batch_op:
        if not _column_exists("watch_signal", "trading_system_code"):
            batch_op.add_column(sa.Column("trading_system_code", sa.String(length=64), nullable=True))
        if not _column_exists("watch_signal", "rule_code"):
            batch_op.add_column(sa.Column("rule_code", sa.String(length=64), nullable=True))
        if not _column_exists("watch_signal", "rule_type"):
            batch_op.add_column(sa.Column("rule_type", sa.String(length=32), nullable=True))
        if not _column_exists("watch_signal", "snapshot_json"):
            batch_op.add_column(sa.Column("snapshot_json", sa.JSON(), nullable=True))
    if not _index_exists("watch_signal", "ix_watch_signal_rule_code"):
        op.create_index("ix_watch_signal_rule_code", "watch_signal", ["rule_code"])


def downgrade() -> None:
    if _index_exists("watch_signal", "ix_watch_signal_rule_code"):
        op.drop_index("ix_watch_signal_rule_code", table_name="watch_signal")
    with op.batch_alter_table("watch_signal") as batch_op:
        if _column_exists("watch_signal", "snapshot_json"):
            batch_op.drop_column("snapshot_json")
        if _column_exists("watch_signal", "rule_type"):
            batch_op.drop_column("rule_type")
        if _column_exists("watch_signal", "rule_code"):
            batch_op.drop_column("rule_code")
        if _column_exists("watch_signal", "trading_system_code"):
            batch_op.drop_column("trading_system_code")
