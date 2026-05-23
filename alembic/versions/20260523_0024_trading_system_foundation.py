"""add trading system foundation tables

Revision ID: 20260523_trading_sys
Revises: 20260522_stock_quote
Create Date: 2026-05-23
"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260523_trading_sys"
down_revision: Union[str, None] = "20260522_stock_quote"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if all(
        _table_exists(table_name)
        for table_name in (
            "trading_system_definition",
            "trading_rule_definition",
            "trading_system_param_definition",
            "trading_system_rule_binding",
        )
    ):
        _seed_trading_system_defaults()
        return

    op.create_table(
        "trading_system_definition",
        sa.Column("system_id", sa.Integer(), nullable=False),
        sa.Column("system_code", sa.String(length=64), nullable=False),
        sa.Column("system_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("lifecycle_desc", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("system_id"),
        sa.UniqueConstraint("system_code", name="uq_trading_system_definition_code"),
    )
    op.create_index(op.f("ix_trading_system_definition_system_code"), "trading_system_definition", ["system_code"])
    op.create_index(op.f("ix_trading_system_definition_system_name"), "trading_system_definition", ["system_name"])
    op.create_index(op.f("ix_trading_system_definition_enabled"), "trading_system_definition", ["enabled"])
    op.create_index(op.f("ix_trading_system_definition_sort_order"), "trading_system_definition", ["sort_order"])
    op.create_index(op.f("ix_trading_system_definition_created_at"), "trading_system_definition", ["created_at"])

    op.create_table(
        "trading_rule_definition",
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column("rule_name", sa.String(length=128), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("executor_key", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("rule_id"),
        sa.UniqueConstraint("rule_code", name="uq_trading_rule_definition_code"),
    )
    op.create_index(op.f("ix_trading_rule_definition_rule_code"), "trading_rule_definition", ["rule_code"])
    op.create_index(op.f("ix_trading_rule_definition_rule_name"), "trading_rule_definition", ["rule_name"])
    op.create_index(op.f("ix_trading_rule_definition_rule_type"), "trading_rule_definition", ["rule_type"])
    op.create_index(op.f("ix_trading_rule_definition_timeframe"), "trading_rule_definition", ["timeframe"])
    op.create_index(op.f("ix_trading_rule_definition_executor_key"), "trading_rule_definition", ["executor_key"])
    op.create_index(op.f("ix_trading_rule_definition_enabled"), "trading_rule_definition", ["enabled"])
    op.create_index(op.f("ix_trading_rule_definition_created_at"), "trading_rule_definition", ["created_at"])

    op.create_table(
        "trading_system_param_definition",
        sa.Column("param_id", sa.Integer(), nullable=False),
        sa.Column("system_code", sa.String(length=64), nullable=False),
        sa.Column("param_key", sa.String(length=64), nullable=False),
        sa.Column("param_name", sa.String(length=128), nullable=False),
        sa.Column("param_type", sa.String(length=32), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("param_id"),
        sa.UniqueConstraint("system_code", "param_key", name="uq_trading_system_param_definition_system_key"),
    )
    op.create_index(op.f("ix_trading_system_param_definition_system_code"), "trading_system_param_definition", ["system_code"])
    op.create_index(op.f("ix_trading_system_param_definition_param_key"), "trading_system_param_definition", ["param_key"])
    op.create_index(op.f("ix_trading_system_param_definition_param_type"), "trading_system_param_definition", ["param_type"])
    op.create_index(op.f("ix_trading_system_param_definition_sort_order"), "trading_system_param_definition", ["sort_order"])
    op.create_index(op.f("ix_trading_system_param_definition_enabled"), "trading_system_param_definition", ["enabled"])
    op.create_index(op.f("ix_trading_system_param_definition_created_at"), "trading_system_param_definition", ["created_at"])
    op.create_index("ix_trading_system_param_system_order", "trading_system_param_definition", ["system_code", "sort_order"])

    op.create_table(
        "trading_system_rule_binding",
        sa.Column("binding_id", sa.Integer(), nullable=False),
        sa.Column("system_code", sa.String(length=64), nullable=False),
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("logic_group", sa.String(length=64), nullable=False),
        sa.Column("logic_operator", sa.String(length=8), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("binding_id"),
        sa.UniqueConstraint("system_code", "rule_code", "stage", name="uq_trading_system_rule_binding_identity"),
    )
    op.create_index(op.f("ix_trading_system_rule_binding_system_code"), "trading_system_rule_binding", ["system_code"])
    op.create_index(op.f("ix_trading_system_rule_binding_rule_code"), "trading_system_rule_binding", ["rule_code"])
    op.create_index(op.f("ix_trading_system_rule_binding_stage"), "trading_system_rule_binding", ["stage"])
    op.create_index(op.f("ix_trading_system_rule_binding_logic_group"), "trading_system_rule_binding", ["logic_group"])
    op.create_index(op.f("ix_trading_system_rule_binding_enabled"), "trading_system_rule_binding", ["enabled"])
    op.create_index(op.f("ix_trading_system_rule_binding_sort_order"), "trading_system_rule_binding", ["sort_order"])
    op.create_index(op.f("ix_trading_system_rule_binding_created_at"), "trading_system_rule_binding", ["created_at"])
    op.create_index("ix_trading_system_rule_binding_system_stage_order", "trading_system_rule_binding", ["system_code", "stage", "sort_order"])
    _seed_trading_system_defaults()


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _seed_trading_system_defaults() -> None:
    conn = op.get_bind()
    if conn.execute(sa.text("select count(*) from trading_system_definition")).scalar() > 0:
        return

    now = datetime.utcnow()
    system_table = sa.table(
        "trading_system_definition",
        sa.column("system_code", sa.String),
        sa.column("system_name", sa.String),
        sa.column("description", sa.Text),
        sa.column("lifecycle_desc", sa.Text),
        sa.column("enabled", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    rule_table = sa.table(
        "trading_rule_definition",
        sa.column("rule_code", sa.String),
        sa.column("rule_name", sa.String),
        sa.column("rule_type", sa.String),
        sa.column("timeframe", sa.String),
        sa.column("executor_key", sa.String),
        sa.column("description", sa.Text),
        sa.column("enabled", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    param_table = sa.table(
        "trading_system_param_definition",
        sa.column("system_code", sa.String),
        sa.column("param_key", sa.String),
        sa.column("param_name", sa.String),
        sa.column("param_type", sa.String),
        sa.column("required", sa.Boolean),
        sa.column("default_value", sa.Text),
        sa.column("description", sa.Text),
        sa.column("sort_order", sa.Integer),
        sa.column("enabled", sa.Boolean),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    binding_table = sa.table(
        "trading_system_rule_binding",
        sa.column("system_code", sa.String),
        sa.column("rule_code", sa.String),
        sa.column("stage", sa.String),
        sa.column("required", sa.Boolean),
        sa.column("logic_group", sa.String),
        sa.column("logic_operator", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("config_json", sa.JSON),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(system_table, [
        {"system_code": "platform_breakout", "system_name": "平台突破", "description": "以平台整理后的突破、回踩和失效条件为核心的交易体系样板。", "lifecycle_desc": "观察 -> 买点确认 -> 交易中 -> 卖出/止损 -> 复盘", "enabled": True, "sort_order": 1, "created_at": now, "updated_at": now},
        {"system_code": "uptrend", "system_name": "上涨趋势", "description": "用于承载趋势跟随类交易规则的体系定义。", "lifecycle_desc": "观察 -> 趋势确认 -> 交易中 -> 卖出/止损 -> 复盘", "enabled": True, "sort_order": 2, "created_at": now, "updated_at": now},
        {"system_code": "limit_relay", "system_name": "涨停接力", "description": "用于承载涨停接力类交易规则的体系定义。", "lifecycle_desc": "观察 -> 接力确认 -> 交易中 -> 卖出/止损 -> 复盘", "enabled": True, "sort_order": 3, "created_at": now, "updated_at": now},
        {"system_code": "oversold_rebound", "system_name": "超跌反弹", "description": "用于承载超跌修复类交易规则的体系定义。", "lifecycle_desc": "观察 -> 反弹确认 -> 交易中 -> 卖出/止损 -> 复盘", "enabled": True, "sort_order": 4, "created_at": now, "updated_at": now},
    ])
    op.bulk_insert(param_table, [
        {"system_code": "platform_breakout", "param_key": "platform_upper_price", "param_name": "箱体上沿", "param_type": "number", "required": True, "default_value": None, "description": "平台箱体上沿价格。", "sort_order": 1, "enabled": True, "created_at": now, "updated_at": now},
        {"system_code": "platform_breakout", "param_key": "platform_support_price", "param_name": "平台支撑位", "param_type": "number", "required": True, "default_value": None, "description": "平台结构的关键支撑价格。", "sort_order": 2, "enabled": True, "created_at": now, "updated_at": now},
        {"system_code": "platform_breakout", "param_key": "key_observe_price", "param_name": "关键观察价", "param_type": "number", "required": True, "default_value": None, "description": "进入观察后的关键跟踪价格。", "sort_order": 3, "enabled": True, "created_at": now, "updated_at": now},
        {"system_code": "platform_breakout", "param_key": "auto_remove_price", "param_name": "自动剔除价", "param_type": "number", "required": False, "default_value": None, "description": "跌破后可用于自动剔除观察的价格。", "sort_order": 4, "enabled": True, "created_at": now, "updated_at": now},
        {"system_code": "platform_breakout", "param_key": "invalid_condition", "param_name": "失效条件", "param_type": "text", "required": True, "default_value": None, "description": "平台突破体系失效的文字化条件。", "sort_order": 5, "enabled": True, "created_at": now, "updated_at": now},
    ])
    op.bulk_insert(rule_table, [
        {"rule_code": "not_break_platform_upper", "rule_name": "不跌破箱体上沿", "rule_type": "filter", "timeframe": "daily", "executor_key": "not_break_price", "description": "平台回踩阶段不跌破箱体上沿。", "enabled": True, "created_at": now, "updated_at": now},
        {"rule_code": "b5_divergence", "rule_name": "5分钟底背离", "rule_type": "buy_signal", "timeframe": "5m", "executor_key": "macd_bottom_divergence", "description": "5分钟 MACD 底背离买点信号。", "enabled": True, "created_at": now, "updated_at": now},
        {"rule_code": "b15_divergence", "rule_name": "15分钟底背离", "rule_type": "buy_signal", "timeframe": "15m", "executor_key": "macd_bottom_divergence", "description": "15分钟 MACD 底背离买点信号。", "enabled": True, "created_at": now, "updated_at": now},
        {"rule_code": "m5_top_divergence", "rule_name": "5分钟顶背离", "rule_type": "sell_signal", "timeframe": "5m", "executor_key": "macd_top_divergence", "description": "5分钟 MACD 顶背离卖出信号。", "enabled": True, "created_at": now, "updated_at": now},
        {"rule_code": "m30_dead_cross", "rule_name": "30分钟死叉", "rule_type": "sell_signal", "timeframe": "30m", "executor_key": "macd_dead_cross", "description": "30分钟 MACD 死叉卖出信号。", "enabled": True, "created_at": now, "updated_at": now},
        {"rule_code": "break_platform_support", "rule_name": "收破平台支撑位", "rule_type": "stop_loss", "timeframe": "daily", "executor_key": "break_price", "description": "日线收破平台支撑位止损信号。", "enabled": True, "created_at": now, "updated_at": now},
    ])
    op.bulk_insert(binding_table, [
        {"system_code": "platform_breakout", "rule_code": "not_break_platform_upper", "stage": "observe", "required": True, "logic_group": "platform_retest", "logic_operator": "AND", "enabled": True, "sort_order": 1, "config_json": {}, "created_at": now, "updated_at": now},
        {"system_code": "platform_breakout", "rule_code": "b5_divergence", "stage": "observe", "required": False, "logic_group": "bottom_divergence", "logic_operator": "OR", "enabled": True, "sort_order": 2, "config_json": {}, "created_at": now, "updated_at": now},
        {"system_code": "platform_breakout", "rule_code": "b15_divergence", "stage": "observe", "required": False, "logic_group": "bottom_divergence", "logic_operator": "OR", "enabled": True, "sort_order": 3, "config_json": {}, "created_at": now, "updated_at": now},
        {"system_code": "platform_breakout", "rule_code": "m5_top_divergence", "stage": "trading", "required": False, "logic_group": "sell_signal", "logic_operator": "OR", "enabled": True, "sort_order": 1, "config_json": {}, "created_at": now, "updated_at": now},
        {"system_code": "platform_breakout", "rule_code": "m30_dead_cross", "stage": "trading", "required": False, "logic_group": "sell_signal", "logic_operator": "OR", "enabled": True, "sort_order": 2, "config_json": {}, "created_at": now, "updated_at": now},
        {"system_code": "platform_breakout", "rule_code": "break_platform_support", "stage": "stop_loss", "required": False, "logic_group": "stop_loss", "logic_operator": "OR", "enabled": True, "sort_order": 1, "config_json": {}, "created_at": now, "updated_at": now},
    ])


def downgrade() -> None:
    op.drop_index("ix_trading_system_rule_binding_system_stage_order", table_name="trading_system_rule_binding")
    op.drop_index(op.f("ix_trading_system_rule_binding_created_at"), table_name="trading_system_rule_binding")
    op.drop_index(op.f("ix_trading_system_rule_binding_sort_order"), table_name="trading_system_rule_binding")
    op.drop_index(op.f("ix_trading_system_rule_binding_enabled"), table_name="trading_system_rule_binding")
    op.drop_index(op.f("ix_trading_system_rule_binding_logic_group"), table_name="trading_system_rule_binding")
    op.drop_index(op.f("ix_trading_system_rule_binding_stage"), table_name="trading_system_rule_binding")
    op.drop_index(op.f("ix_trading_system_rule_binding_rule_code"), table_name="trading_system_rule_binding")
    op.drop_index(op.f("ix_trading_system_rule_binding_system_code"), table_name="trading_system_rule_binding")
    op.drop_table("trading_system_rule_binding")

    op.drop_index("ix_trading_system_param_system_order", table_name="trading_system_param_definition")
    op.drop_index(op.f("ix_trading_system_param_definition_created_at"), table_name="trading_system_param_definition")
    op.drop_index(op.f("ix_trading_system_param_definition_enabled"), table_name="trading_system_param_definition")
    op.drop_index(op.f("ix_trading_system_param_definition_sort_order"), table_name="trading_system_param_definition")
    op.drop_index(op.f("ix_trading_system_param_definition_param_type"), table_name="trading_system_param_definition")
    op.drop_index(op.f("ix_trading_system_param_definition_param_key"), table_name="trading_system_param_definition")
    op.drop_index(op.f("ix_trading_system_param_definition_system_code"), table_name="trading_system_param_definition")
    op.drop_table("trading_system_param_definition")

    op.drop_index(op.f("ix_trading_rule_definition_created_at"), table_name="trading_rule_definition")
    op.drop_index(op.f("ix_trading_rule_definition_enabled"), table_name="trading_rule_definition")
    op.drop_index(op.f("ix_trading_rule_definition_executor_key"), table_name="trading_rule_definition")
    op.drop_index(op.f("ix_trading_rule_definition_timeframe"), table_name="trading_rule_definition")
    op.drop_index(op.f("ix_trading_rule_definition_rule_type"), table_name="trading_rule_definition")
    op.drop_index(op.f("ix_trading_rule_definition_rule_name"), table_name="trading_rule_definition")
    op.drop_index(op.f("ix_trading_rule_definition_rule_code"), table_name="trading_rule_definition")
    op.drop_table("trading_rule_definition")

    op.drop_index(op.f("ix_trading_system_definition_created_at"), table_name="trading_system_definition")
    op.drop_index(op.f("ix_trading_system_definition_sort_order"), table_name="trading_system_definition")
    op.drop_index(op.f("ix_trading_system_definition_enabled"), table_name="trading_system_definition")
    op.drop_index(op.f("ix_trading_system_definition_system_name"), table_name="trading_system_definition")
    op.drop_index(op.f("ix_trading_system_definition_system_code"), table_name="trading_system_definition")
    op.drop_table("trading_system_definition")
