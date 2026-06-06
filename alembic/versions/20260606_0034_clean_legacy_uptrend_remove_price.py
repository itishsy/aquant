from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op


revision = "20260606_clean_legacy_uptrend_remove_price"
down_revision = "20260606_uptrend_rule_remove_schedule"
branch_labels = None
depends_on = None


def _json_object(value) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, system_params_json FROM watch_pool "
            "WHERE trading_system_code = 'uptrend' "
            "OR trading_system IN ('uptrend', '趋势', '上涨趋势')"
        )
    ).fetchall()
    for row in rows:
        params = _json_object(row[1])
        params.pop("auto_remove_price", None)
        conn.execute(
            sa.text(
                "UPDATE watch_pool SET auto_remove_price = NULL, system_params_json = :params "
                "WHERE id = :watch_id"
            ),
            {"params": json.dumps(params, ensure_ascii=False), "watch_id": row[0]},
        )


def downgrade() -> None:
    pass
