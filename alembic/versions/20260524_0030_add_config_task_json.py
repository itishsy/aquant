from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260524_task_config_json"
down_revision = "20260524_unified_kline"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    with op.batch_alter_table("config_task") as batch_op:
        if not _column_exists("config_task", "config_json"):
            batch_op.add_column(sa.Column("config_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("config_task") as batch_op:
        if _column_exists("config_task", "config_json"):
            batch_op.drop_column("config_json")
