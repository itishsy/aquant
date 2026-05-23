from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260524_signal_notify"
down_revision = "20260524_signal_rules"
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
        if not _column_exists("watch_signal", "notification_sent"):
            batch_op.add_column(sa.Column("notification_sent", sa.Boolean(), nullable=False, server_default=sa.false()))
        if not _column_exists("watch_signal", "notification_sent_at"):
            batch_op.add_column(sa.Column("notification_sent_at", sa.DateTime(), nullable=True))
        if not _column_exists("watch_signal", "notification_error"):
            batch_op.add_column(sa.Column("notification_error", sa.Text(), nullable=True))
    if not _index_exists("watch_signal", "ix_watch_signal_notification_sent"):
        op.create_index("ix_watch_signal_notification_sent", "watch_signal", ["notification_sent"])


def downgrade() -> None:
    if _index_exists("watch_signal", "ix_watch_signal_notification_sent"):
        op.drop_index("ix_watch_signal_notification_sent", table_name="watch_signal")
    with op.batch_alter_table("watch_signal") as batch_op:
        if _column_exists("watch_signal", "notification_error"):
            batch_op.drop_column("notification_error")
        if _column_exists("watch_signal", "notification_sent_at"):
            batch_op.drop_column("notification_sent_at")
        if _column_exists("watch_signal", "notification_sent"):
            batch_op.drop_column("notification_sent")
