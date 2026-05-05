"""prd v1 alignment tables

Revision ID: 20260505_0003
Revises: 20260430_0002
Create Date: 2026-05-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.models import entities


revision = "20260505_0003"
down_revision = "20260430_0002"
branch_labels = None
depends_on = None


SYSTEM_TABLES = [
    entities.MktDaily.__table__,
    entities.MktHotBoard.__table__,
    entities.MktHotStock.__table__,
    entities.MktLimitUp.__table__,
    entities.WatchSignal.__table__,
    entities.WatchSignalPerformance.__table__,
    entities.WatchPoolStatusLog.__table__,
    entities.WatchTrade.__table__,
    entities.WatchTradeExecution.__table__,
    entities.ReviewForm.__table__,
    entities.ReviewWeekly.__table__,
    entities.ReviewMonthly.__table__,
    entities.ReviewTrade.__table__,
    entities.MyUserProfile.__table__,
    entities.MyUserPreference.__table__,
    entities.MyNotificationSetting.__table__,
    entities.ConfigDataSource.__table__,
    entities.ConfigTask.__table__,
    entities.ConfigTaskLog.__table__,
    entities.ConfigFieldMapping.__table__,
    entities.ConfigDictionary.__table__,
    entities.ConfigStrategy.__table__,
    entities.ConfigNotificationTemplate.__table__,
    entities.ConfigNotificationRecord.__table__,
    entities.ConfigReviewTemplate.__table__,
    entities.ConfigOperationLog.__table__,
]


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_columns(table_name: str, columns: list[sa.Column]) -> None:
    existing = _columns(table_name)
    for column in columns:
        if column.name not in existing:
            op.add_column(table_name, column)


def _create_index(name: str, table_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if name not in existing:
        op.create_index(name, table_name, columns)


def upgrade() -> None:
    bind = op.get_bind()
    for table in SYSTEM_TABLES:
        table.create(bind=bind, checkfirst=True)

    _add_columns(
        "watch_pool",
        [
            sa.Column("pool_status", sa.String(length=32), nullable=False, server_default="观察中"),
            sa.Column("monitor_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("operation_strategies", sa.JSON(), nullable=True),
            sa.Column("buy_point_types", sa.JSON(), nullable=True),
            sa.Column("source_type", sa.String(length=64), nullable=True),
            sa.Column("source_platform", sa.String(length=64), nullable=True),
            sa.Column("source_rank", sa.Integer(), nullable=True),
            sa.Column("source_score", sa.Float(), nullable=True),
            sa.Column("source_reason", sa.Text(), nullable=True),
            sa.Column("xueqiu_url", sa.String(length=512), nullable=True),
            sa.Column("entry_price", sa.Float(), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("removed_at", sa.DateTime(), nullable=True),
        ],
    )
    _create_index("ix_watch_pool_pool_status", "watch_pool", ["pool_status"])


def downgrade() -> None:
    # Additive migration. Keep user data intact on downgrade.
    pass
