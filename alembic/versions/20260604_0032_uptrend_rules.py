from __future__ import annotations

import json
from datetime import datetime

import sqlalchemy as sa
from alembic import op


revision = "20260604_uptrend_rules"
down_revision = "20260604_remove_removed_rule_executors"
branch_labels = None
depends_on = None

NEW_RULES = [
    (
        "uptrend_not_break_ma20",
        "趋势不跌破MA20",
        "filter",
        "daily",
        "ma_trend",
        "趋势观察阶段，股价不低于MA20的前置过滤条件。",
    ),
    (
        "uptrend_break_ma20_consecutive_remove",
        "连续3日跌破MA20剔除",
        "remove_signal",
        "daily",
        "break_ma",
        "连续3个交易日收盘价全部低于MA20，自动剔除观察。",
    ),
]

NEW_BINDINGS = [
    (
        "uptrend",
        "uptrend_not_break_ma20",
        "observe",
        True,
        "trend_filter",
        "AND",
        1,
        {
            "data": {"timeframe": "daily", "lookback_bars": 60, "indicators": ["ma"]},
            "signal": {"mode": "price_not_below_ma", "ma": 20},
        },
    ),
    (
        "uptrend",
        "uptrend_break_ma20_consecutive_remove",
        "observe",
        False,
        "remove",
        "OR",
        10,
        {
            "data": {"timeframe": "daily", "lookback_bars": 60, "indicators": ["ma"]},
            "signal": {"break_type": "consecutive_below", "ma": 20, "consecutive_bars": 3},
        },
    ),
]

EXISTING_DIVERGENCE_RULE_CODES = ("b5_divergence", "b15_divergence")
TARGET_TASK_INTERVALS = {
    "prepare_watch_kline_data": 15,
    "scan_watch_rules": 15,
}


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.utcnow()

    # Insert new rule definitions
    for rule_code, rule_name, rule_type, timeframe, executor_key, description in NEW_RULES:
        existing = conn.execute(
            sa.text("SELECT 1 FROM trading_rule_definition WHERE rule_code = :rc"),
            {"rc": rule_code},
        ).fetchone()
        if not existing:
            conn.execute(
                sa.text(
                    "INSERT INTO trading_rule_definition "
                    "(rule_code, rule_name, rule_type, timeframe, executor_key, description, enabled, created_at, updated_at) "
                    "VALUES (:rc, :rn, :rt, :tf, :ek, :desc, 1, :created_at, :updated_at)"
                ),
                {
                    "rc": rule_code,
                    "rn": rule_name,
                    "rt": rule_type,
                    "tf": timeframe,
                    "ek": executor_key,
                    "desc": description,
                    "created_at": now,
                    "updated_at": now,
                },
            )

    # Insert new bindings
    for (system_code, rule_code, stage, required, logic_group,
         logic_operator, sort_order, config_json) in NEW_BINDINGS:
        existing = conn.execute(
            sa.text(
                "SELECT 1 FROM trading_system_rule_binding "
                "WHERE system_code = :sc AND rule_code = :rc AND stage = :st"
            ),
            {"sc": system_code, "rc": rule_code, "st": stage},
        ).fetchone()
        if not existing:
            conn.execute(
                sa.text(
                    "INSERT INTO trading_system_rule_binding "
                    "(system_code, rule_code, stage, required, logic_group, logic_operator, "
                    "sort_order, enabled, config_json, created_at, updated_at) "
                    "VALUES (:sc, :rc, :st, :req, :lg, :lo, :so, 1, :cj, :created_at, :updated_at)"
                ),
                {
                    "sc": system_code,
                    "rc": rule_code,
                    "st": stage,
                    "req": required,
                    "lg": logic_group,
                    "lo": logic_operator,
                    "so": sort_order,
                    "cj": json.dumps(config_json, ensure_ascii=False),
                    "created_at": now,
                    "updated_at": now,
                },
            )

    # Add after_watch_added to existing b5_divergence / b15_divergence bindings
    for rule_code in EXISTING_DIVERGENCE_RULE_CODES:
        row = conn.execute(
            sa.text(
                "SELECT binding_id, config_json FROM trading_system_rule_binding "
                "WHERE system_code = 'uptrend' AND rule_code = :rc AND stage = 'observe'"
            ),
            {"rc": rule_code},
        ).fetchone()
        if not row:
            continue
        try:
            config = json.loads(row[1]) if isinstance(row[1], str) else (row[1] or {})
        except (json.JSONDecodeError, TypeError):
            config = {}
        if not isinstance(config, dict):
            config = {}
        signal = dict(config.get("signal") or {})
        if signal.get("after_watch_added") is not True:
            signal["after_watch_added"] = True
            config["signal"] = signal
            conn.execute(
                sa.text(
                    "UPDATE trading_system_rule_binding SET config_json = :cj "
                    "WHERE binding_id = :bid"
                ),
                {"cj": json.dumps(config, ensure_ascii=False), "bid": row[0]},
            )

    # Keep existing task-management configuration aligned with the new scheduler cadence.
    for task_name, interval_minutes in TARGET_TASK_INTERVALS.items():
        row = conn.execute(
            sa.text("SELECT task_id, config_json FROM config_task WHERE task_name = :task_name"),
            {"task_name": task_name},
        ).fetchone()
        if not row:
            continue
        try:
            config = json.loads(row[1]) if isinstance(row[1], str) else (row[1] or {})
        except (json.JSONDecodeError, TypeError):
            config = {}
        if not isinstance(config, dict):
            config = {}
        config["interval_minutes"] = interval_minutes
        conn.execute(
            sa.text("UPDATE config_task SET config_json = :config_json WHERE task_id = :task_id"),
            {"config_json": json.dumps(config, ensure_ascii=False), "task_id": row[0]},
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove new bindings
    conn.execute(
        sa.text(
            "DELETE FROM trading_system_rule_binding "
            "WHERE system_code = 'uptrend' AND rule_code IN ('uptrend_not_break_ma20', 'uptrend_break_ma20_consecutive_remove')"
        )
    )

    # Remove after_watch_added from b5_divergence / b15_divergence bindings
    for rule_code in EXISTING_DIVERGENCE_RULE_CODES:
        row = conn.execute(
            sa.text(
                "SELECT binding_id, config_json FROM trading_system_rule_binding "
                "WHERE system_code = 'uptrend' AND rule_code = :rc AND stage = 'observe'"
            ),
            {"rc": rule_code},
        ).fetchone()
        if not row or not row[1]:
            continue
        try:
            config = json.loads(row[1]) if isinstance(row[1], str) else row[1]
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(config, dict) and isinstance(config.get("signal"), dict):
            config["signal"].pop("after_watch_added", None)
            conn.execute(
                sa.text(
                    "UPDATE trading_system_rule_binding SET config_json = :cj "
                    "WHERE binding_id = :bid"
                ),
                {"cj": json.dumps(config, ensure_ascii=False), "bid": row[0]},
            )

    # Remove new rules
    conn.execute(
        sa.text(
            "DELETE FROM trading_rule_definition "
            "WHERE rule_code IN ('uptrend_not_break_ma20', 'uptrend_break_ma20_consecutive_remove')"
        )
    )
