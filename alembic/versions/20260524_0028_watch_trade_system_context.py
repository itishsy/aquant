from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260524_trade_context"
down_revision = "20260524_signal_notify"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    with op.batch_alter_table("watch_trade") as batch_op:
        if not _column_exists("watch_trade", "trading_system_code"):
            batch_op.add_column(sa.Column("trading_system_code", sa.String(length=64), nullable=True))
        if not _column_exists("watch_trade", "entry_rule_code"):
            batch_op.add_column(sa.Column("entry_rule_code", sa.String(length=64), nullable=True))
        if not _column_exists("watch_trade", "system_params_json"):
            batch_op.add_column(sa.Column("system_params_json", sa.JSON(), nullable=True))
        if not _column_exists("watch_trade", "active_sell_rule_codes_json"):
            batch_op.add_column(sa.Column("active_sell_rule_codes_json", sa.JSON(), nullable=True))
        if not _column_exists("watch_trade", "active_stop_rule_codes_json"):
            batch_op.add_column(sa.Column("active_stop_rule_codes_json", sa.JSON(), nullable=True))
        if not _column_exists("watch_trade", "current_stage"):
            batch_op.add_column(sa.Column("current_stage", sa.String(length=32), nullable=False, server_default="trading"))
        if not _column_exists("watch_trade", "latest_trade_signal_id"):
            batch_op.add_column(sa.Column("latest_trade_signal_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("watch_trade") as batch_op:
        if _column_exists("watch_trade", "latest_trade_signal_id"):
            batch_op.drop_column("latest_trade_signal_id")
        if _column_exists("watch_trade", "current_stage"):
            batch_op.drop_column("current_stage")
        if _column_exists("watch_trade", "active_stop_rule_codes_json"):
            batch_op.drop_column("active_stop_rule_codes_json")
        if _column_exists("watch_trade", "active_sell_rule_codes_json"):
            batch_op.drop_column("active_sell_rule_codes_json")
        if _column_exists("watch_trade", "system_params_json"):
            batch_op.drop_column("system_params_json")
        if _column_exists("watch_trade", "entry_rule_code"):
            batch_op.drop_column("entry_rule_code")
        if _column_exists("watch_trade", "trading_system_code"):
            batch_op.drop_column("trading_system_code")
