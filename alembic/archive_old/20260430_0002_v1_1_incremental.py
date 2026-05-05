"""v1.1 incremental training workflow tables

Revision ID: 20260430_0002
Revises: 20260426_0001
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.models import entities


revision = "20260430_0002"
down_revision = "20260426_0001"
branch_labels = None
depends_on = None


NEW_TABLES = [
    entities.WatchPoolLifecycle.__table__,
    entities.WatchPoolScore.__table__,
    entities.DailyTradePlan.__table__,
    entities.DailyTradePlanItem.__table__,
    entities.TradeExecutionChecklist.__table__,
    entities.SellPlan.__table__,
    entities.TradeErrorTag.__table__,
    entities.TradeReviewDetail.__table__,
    entities.WeeklyReview.__table__,
    entities.MonthlyReview.__table__,
    entities.DisciplineRule.__table__,
    entities.UserTradingScore.__table__,
    entities.NotificationRecord.__table__,
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
    for table in NEW_TABLES:
        table.create(bind=bind, checkfirst=True)

    _add_columns(
        "watch_pool",
        [
            sa.Column("lifecycle_status", sa.String(length=32), nullable=False, server_default="watching"),
            sa.Column("pool_layer", sa.String(length=32), nullable=False, server_default="L2_watch"),
            sa.Column("entry_source", sa.String(length=64), nullable=True),
            sa.Column("entry_score", sa.Float(), nullable=True),
            sa.Column("entry_level", sa.String(length=32), nullable=True),
            sa.Column("sector_status", sa.String(length=32), nullable=True),
            sa.Column("observe_start_date", sa.Date(), nullable=True),
            sa.Column("max_observe_days", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("next_action", sa.Text(), nullable=True),
            sa.Column("archive_reason", sa.Text(), nullable=True),
            sa.Column("archived_at", sa.DateTime(), nullable=True),
        ],
    )
    _add_columns(
        "trade_record",
        [
            sa.Column("plan_id", sa.Integer(), nullable=True),
            sa.Column("plan_item_id", sa.Integer(), nullable=True),
            sa.Column("is_unplanned", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("discipline_flags", sa.JSON(), nullable=True),
            sa.Column("review_status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("trade_score", sa.Float(), nullable=True),
        ],
    )
    _add_columns(
        "signal_record",
        [
            sa.Column("plan_item_id", sa.Integer(), nullable=True),
            sa.Column("checklist_required", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("signal_invalidated_at", sa.DateTime(), nullable=True),
            sa.Column("invalid_reason", sa.Text(), nullable=True),
        ],
    )

    _create_index("ix_watch_pool_lifecycle_status", "watch_pool", ["lifecycle_status"])
    _create_index("ix_watch_pool_pool_layer", "watch_pool", ["pool_layer"])
    _create_index("ix_trade_record_plan_id", "trade_record", ["plan_id"])
    _create_index("ix_trade_record_plan_item_id", "trade_record", ["plan_item_id"])
    _create_index("ix_signal_record_plan_item_id", "signal_record", ["plan_item_id"])


def downgrade() -> None:
    # v1.1 is additive. Avoid destructive downgrade that may erase user training history.
    pass
