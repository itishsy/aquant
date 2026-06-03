from __future__ import annotations

import json

from alembic import op


revision = "20260603_replace_break_price"
down_revision = "20260524_task_config_json"
branch_labels = None
depends_on = None


BREAK_SUPPORT_CONFIG = {
    "data": {"timeframe": "daily", "lookback_bars": 5, "indicators": []},
    "signal": {"target_param": "platform_support_price", "break_type": "close_below", "threshold_pct": 0},
}


def upgrade() -> None:
    op.execute(
        "UPDATE trading_rule_definition "
        "SET executor_key = 'break_level' "
        "WHERE rule_code = 'break_platform_support' AND executor_key = 'break_price'"
    )
    config_json = json.dumps(BREAK_SUPPORT_CONFIG, ensure_ascii=False)
    op.execute(
        "UPDATE trading_system_rule_binding "
        f"SET config_json = '{config_json}' "
        "WHERE rule_code = 'break_platform_support' "
        "AND (config_json IS NULL OR config_json = '' OR config_json = '{}')"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE trading_rule_definition "
        "SET executor_key = 'break_price' "
        "WHERE rule_code = 'break_platform_support' AND executor_key = 'break_level'"
    )
