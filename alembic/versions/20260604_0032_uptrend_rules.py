from __future__ import annotations

import json

from alembic import op


revision = "20260604_uptrend_rules"
down_revision = "20260603_replace_break_price"
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


def upgrade() -> None:
    conn = op.get_bind()

    # Insert new rule definitions
    for rule_code, rule_name, rule_type, timeframe, executor_key, description in NEW_RULES:
        existing = conn.execute(
            "SELECT 1 FROM trading_rule_definition WHERE rule_code = :rc",
            {"rc": rule_code},
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO trading_rule_definition "
                "(rule_code, rule_name, rule_type, timeframe, executor_key, description, enabled) "
                "VALUES (:rc, :rn, :rt, :tf, :ek, :desc, 1)",
                {
                    "rc": rule_code,
                    "rn": rule_name,
                    "rt": rule_type,
                    "tf": timeframe,
                    "ek": executor_key,
                    "desc": description,
                },
            )

    # Insert new bindings
    for (system_code, rule_code, stage, required, logic_group,
         logic_operator, sort_order, config_json) in NEW_BINDINGS:
        existing = conn.execute(
            "SELECT 1 FROM trading_system_rule_binding "
            "WHERE system_code = :sc AND rule_code = :rc AND stage = :st",
            {"sc": system_code, "rc": rule_code, "st": stage},
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO trading_system_rule_binding "
                "(system_code, rule_code, stage, required, logic_group, logic_operator, "
                "sort_order, enabled, config_json) "
                "VALUES (:sc, :rc, :st, :req, :lg, :lo, :so, 1, :cj)",
                {
                    "sc": system_code,
                    "rc": rule_code,
                    "st": stage,
                    "req": required,
                    "lg": logic_group,
                    "lo": logic_operator,
                    "so": sort_order,
                    "cj": json.dumps(config_json, ensure_ascii=False),
                },
            )

    # Add after_watch_added to existing b5_divergence / b15_divergence bindings
    for rule_code in EXISTING_DIVERGENCE_RULE_CODES:
        row = conn.execute(
            "SELECT binding_id, config_json FROM trading_system_rule_binding "
            "WHERE system_code = 'uptrend' AND rule_code = :rc AND stage = 'observe'",
            {"rc": rule_code},
        ).fetchone()
        if not row or not row[1]:
            continue
        try:
            config = json.loads(row[1]) if isinstance(row[1], str) else row[1]
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(config, dict):
            continue
        signal = config.get("signal")
        if isinstance(signal, dict) and signal.get("after_watch_added") is not True:
            signal["after_watch_added"] = True
            config["signal"] = signal
            conn.execute(
                "UPDATE trading_system_rule_binding SET config_json = :cj "
                "WHERE binding_id = :bid",
                {"cj": json.dumps(config, ensure_ascii=False), "bid": row[0]},
            )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove new bindings
    conn.execute(
        "DELETE FROM trading_system_rule_binding "
        "WHERE system_code = 'uptrend' AND rule_code IN ('uptrend_not_break_ma20', 'uptrend_break_ma20_consecutive_remove')"
    )

    # Remove after_watch_added from b5_divergence / b15_divergence bindings
    for rule_code in EXISTING_DIVERGENCE_RULE_CODES:
        row = conn.execute(
            "SELECT binding_id, config_json FROM trading_system_rule_binding "
            "WHERE system_code = 'uptrend' AND rule_code = :rc AND stage = 'observe'",
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
                "UPDATE trading_system_rule_binding SET config_json = :cj "
                "WHERE binding_id = :bid",
                {"cj": json.dumps(config, ensure_ascii=False), "bid": row[0]},
            )

    # Remove new rules
    conn.execute(
        "DELETE FROM trading_rule_definition "
        "WHERE rule_code IN ('uptrend_not_break_ma20', 'uptrend_break_ma20_consecutive_remove')"
    )
