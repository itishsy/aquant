"""Normalize market daily extension data into child tables.

Revision ID: 20260510_0005
Revises: 20260510_0004
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260510_0005"
down_revision = "20260510_0004"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    if not _has_table("mkt_daily_chance"):
        op.create_table(
            "mkt_daily_chance",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("rank_no", sa.Integer(), nullable=True),
            sa.Column("subject_id", sa.Integer(), nullable=True),
            sa.Column("subject_name", sa.String(length=128), nullable=False),
            sa.Column("article_id", sa.Integer(), nullable=True),
            sa.Column("article_title", sa.Text(), nullable=False),
            sa.Column("article_time", sa.Integer(), nullable=True),
            sa.Column("attention_num", sa.Integer(), nullable=True),
            sa.Column("source_update_time", sa.DateTime(), nullable=True),
            sa.Column("collected_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("trade_date", "source", "subject_id", name="uq_mkt_daily_chance_day_source_subject"),
        )
        op.create_index("ix_mkt_daily_chance_trade_date", "mkt_daily_chance", ["trade_date"])
        op.create_index("ix_mkt_daily_chance_source", "mkt_daily_chance", ["source"])
        op.create_index("ix_mkt_daily_chance_platform", "mkt_daily_chance", ["platform"])
        op.create_index("ix_mkt_daily_chance_subject_id", "mkt_daily_chance", ["subject_id"])
        op.create_index("ix_mkt_daily_chance_subject_name", "mkt_daily_chance", ["subject_name"])

    if not _has_table("mkt_daily_chance_stock"):
        op.create_table(
            "mkt_daily_chance_stock",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("chance_id", sa.Integer(), nullable=False),
            sa.Column("stock_code", sa.String(length=16), nullable=False),
            sa.Column("stock_name", sa.String(length=64), nullable=False),
            sa.Column("change_pct", sa.Float(), nullable=True),
            sa.Column("last_price", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("chance_id", "stock_code", name="uq_mkt_daily_chance_stock"),
        )
        op.create_index("ix_mkt_daily_chance_stock_chance_id", "mkt_daily_chance_stock", ["chance_id"])
        op.create_index("ix_mkt_daily_chance_stock_stock_code", "mkt_daily_chance_stock", ["stock_code"])

    if not _has_table("mkt_daily_tuyere"):
        op.create_table(
            "mkt_daily_tuyere",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("rank_no", sa.Integer(), nullable=True),
            sa.Column("subject_id", sa.Integer(), nullable=True),
            sa.Column("subject_name", sa.String(length=128), nullable=False),
            sa.Column("driver", sa.Text(), nullable=False),
            sa.Column("attention_num", sa.Integer(), nullable=True),
            sa.Column("source_update_time", sa.DateTime(), nullable=True),
            sa.Column("collected_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("trade_date", "source", "subject_id", name="uq_mkt_daily_tuyere_day_source_subject"),
        )
        op.create_index("ix_mkt_daily_tuyere_trade_date", "mkt_daily_tuyere", ["trade_date"])
        op.create_index("ix_mkt_daily_tuyere_source", "mkt_daily_tuyere", ["source"])
        op.create_index("ix_mkt_daily_tuyere_platform", "mkt_daily_tuyere", ["platform"])
        op.create_index("ix_mkt_daily_tuyere_subject_id", "mkt_daily_tuyere", ["subject_id"])
        op.create_index("ix_mkt_daily_tuyere_subject_name", "mkt_daily_tuyere", ["subject_name"])

    if not _has_table("mkt_daily_tuyere_stock"):
        op.create_table(
            "mkt_daily_tuyere_stock",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tuyere_id", sa.Integer(), nullable=False),
            sa.Column("stock_code", sa.String(length=16), nullable=False),
            sa.Column("stock_name", sa.String(length=64), nullable=False),
            sa.Column("change_pct", sa.Float(), nullable=True),
            sa.Column("last_price", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("tuyere_id", "stock_code", name="uq_mkt_daily_tuyere_stock"),
        )
        op.create_index("ix_mkt_daily_tuyere_stock_tuyere_id", "mkt_daily_tuyere_stock", ["tuyere_id"])
        op.create_index("ix_mkt_daily_tuyere_stock_stock_code", "mkt_daily_tuyere_stock", ["stock_code"])

    if not _has_table("mkt_daily_topic"):
        op.create_table(
            "mkt_daily_topic",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("rank_no", sa.Integer(), nullable=True),
            sa.Column("topic_code", sa.String(length=64), nullable=False),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("subtitle", sa.Text(), nullable=False),
            sa.Column("hot_value", sa.Float(), nullable=True),
            sa.Column("jump_url", sa.String(length=512), nullable=True),
            sa.Column("source_update_time", sa.DateTime(), nullable=True),
            sa.Column("collected_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("trade_date", "source", "topic_code", name="uq_mkt_daily_topic_day_source_code"),
        )
        op.create_index("ix_mkt_daily_topic_trade_date", "mkt_daily_topic", ["trade_date"])
        op.create_index("ix_mkt_daily_topic_source", "mkt_daily_topic", ["source"])
        op.create_index("ix_mkt_daily_topic_platform", "mkt_daily_topic", ["platform"])
        op.create_index("ix_mkt_daily_topic_topic_code", "mkt_daily_topic", ["topic_code"])

    if not _has_table("mkt_daily_topic_stock"):
        op.create_table(
            "mkt_daily_topic_stock",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("topic_id", sa.Integer(), nullable=False),
            sa.Column("stock_code", sa.String(length=16), nullable=False),
            sa.Column("stock_name", sa.String(length=64), nullable=False),
            sa.Column("change_pct", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("topic_id", "stock_code", name="uq_mkt_daily_topic_stock"),
        )
        op.create_index("ix_mkt_daily_topic_stock_topic_id", "mkt_daily_topic_stock", ["topic_id"])
        op.create_index("ix_mkt_daily_topic_stock_stock_code", "mkt_daily_topic_stock", ["stock_code"])

    if not _has_table("mkt_limit_up_ladder"):
        op.create_table(
            "mkt_limit_up_ladder",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("trade_date", sa.Date(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("platform", sa.String(length=32), nullable=False),
            sa.Column("height", sa.Integer(), nullable=False),
            sa.Column("stock_count", sa.Integer(), nullable=False),
            sa.Column("source_update_time", sa.DateTime(), nullable=True),
            sa.Column("collected_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("trade_date", "source", "height", name="uq_mkt_limit_ladder_day_source_height"),
        )
        op.create_index("ix_mkt_limit_up_ladder_trade_date", "mkt_limit_up_ladder", ["trade_date"])
        op.create_index("ix_mkt_limit_up_ladder_source", "mkt_limit_up_ladder", ["source"])
        op.create_index("ix_mkt_limit_up_ladder_platform", "mkt_limit_up_ladder", ["platform"])
        op.create_index("ix_mkt_limit_up_ladder_height", "mkt_limit_up_ladder", ["height"])

    if not _has_table("mkt_limit_up_ladder_stock"):
        op.create_table(
            "mkt_limit_up_ladder_stock",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("ladder_id", sa.Integer(), nullable=False),
            sa.Column("stock_code", sa.String(length=16), nullable=False),
            sa.Column("stock_name", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("ladder_id", "stock_code", name="uq_mkt_limit_ladder_stock"),
        )
        op.create_index("ix_mkt_limit_up_ladder_stock_ladder_id", "mkt_limit_up_ladder_stock", ["ladder_id"])
        op.create_index("ix_mkt_limit_up_ladder_stock_stock_code", "mkt_limit_up_ladder_stock", ["stock_code"])

    for column_name in ("today_chances", "today_tuyeres", "topic_list", "limit_up_ladder"):
        _drop_column_if_exists("mkt_daily", column_name)


def downgrade() -> None:
    for column_name in ("today_chances", "today_tuyeres", "topic_list", "limit_up_ladder"):
        if not _has_column("mkt_daily", column_name):
            op.add_column("mkt_daily", sa.Column(column_name, sa.JSON(), nullable=True))

    for table_name in (
        "mkt_limit_up_ladder_stock",
        "mkt_limit_up_ladder",
        "mkt_daily_topic_stock",
        "mkt_daily_topic",
        "mkt_daily_tuyere_stock",
        "mkt_daily_tuyere",
        "mkt_daily_chance_stock",
        "mkt_daily_chance",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)
