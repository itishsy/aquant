from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260524_unified_kline"
down_revision = "20260524_trade_context"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _table_exists("mkt_stock_kline"):
        return
    op.create_table(
        "mkt_stock_kline",
        sa.Column("kline_id", sa.Integer(), primary_key=True),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("kline_time", sa.DateTime(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open_price", sa.Float(), nullable=False),
        sa.Column("high_price", sa.Float(), nullable=False),
        sa.Column("low_price", sa.Float(), nullable=False),
        sa.Column("close_price", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False, server_default="0"),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="mock"),
        sa.Column("source_update_time", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("stock_code", "timeframe", "kline_time", "source", name="uq_mkt_stock_kline_code_tf_time_source"),
    )
    op.create_index("ix_mkt_stock_kline_stock_code", "mkt_stock_kline", ["stock_code"])
    op.create_index("ix_mkt_stock_kline_timeframe", "mkt_stock_kline", ["timeframe"])
    op.create_index("ix_mkt_stock_kline_kline_time", "mkt_stock_kline", ["kline_time"])
    op.create_index("ix_mkt_stock_kline_trade_date", "mkt_stock_kline", ["trade_date"])
    op.create_index("ix_mkt_stock_kline_source", "mkt_stock_kline", ["source"])
    op.create_index("ix_mkt_stock_kline_created_at", "mkt_stock_kline", ["created_at"])
    op.create_index("ix_mkt_stock_kline_code_tf_time", "mkt_stock_kline", ["stock_code", "timeframe", "kline_time"])
    op.create_index("ix_mkt_stock_kline_code_tf_date", "mkt_stock_kline", ["stock_code", "timeframe", "trade_date"])


def downgrade() -> None:
    if _table_exists("mkt_stock_kline"):
        op.drop_table("mkt_stock_kline")
