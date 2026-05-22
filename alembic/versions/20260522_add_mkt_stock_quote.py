"""add latest stock quote table

Revision ID: 20260522_stock_quote
Revises: 20260521_auto_remove
Create Date: 2026-05-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260522_stock_quote"
down_revision: Union[str, None] = "20260521_auto_remove"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mkt_stock_quote",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("stock_name", sa.String(length=64), nullable=False),
        sa.Column("latest_price", sa.Float(), nullable=True),
        sa.Column("change_pct", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_update_time", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stock_code", name="uq_mkt_stock_quote_code"),
    )
    op.create_index(op.f("ix_mkt_stock_quote_stock_code"), "mkt_stock_quote", ["stock_code"], unique=False)
    op.create_index(op.f("ix_mkt_stock_quote_created_at"), "mkt_stock_quote", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mkt_stock_quote_created_at"), table_name="mkt_stock_quote")
    op.drop_index(op.f("ix_mkt_stock_quote_stock_code"), table_name="mkt_stock_quote")
    op.drop_table("mkt_stock_quote")
