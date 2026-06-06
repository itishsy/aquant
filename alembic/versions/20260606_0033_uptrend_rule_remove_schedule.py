from __future__ import annotations

import json
from datetime import datetime

import sqlalchemy as sa
from alembic import op


revision = "20260606_uptrend_rule_remove_schedule"
down_revision = "20260604_uptrend_rules"
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
    now = datetime.utcnow()

    rows = conn.execute(
        sa.text(
            "SELECT id, system_params_json FROM watch_pool "
            "WHERE trading_system_code = 'uptrend' OR trading_system = 'uptrend'"
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

    task = conn.execute(
        sa.text("SELECT task_id FROM config_task WHERE task_name = 'scan_watch_remove_rules'")
    ).fetchone()
    config_json = json.dumps({"hour": 20, "minute": 0}, ensure_ascii=False)
    if task:
        conn.execute(
            sa.text(
                "UPDATE config_task SET task_type = 'scheduled', owner_module = 'signal', "
                "cron_expression = '0 20 * * *', enabled = 1, config_json = :config_json, "
                "updated_at = :updated_at WHERE task_id = :task_id"
            ),
            {"config_json": config_json, "updated_at": now, "task_id": task[0]},
        )
    else:
        conn.execute(
            sa.text(
                "INSERT INTO config_task "
                "(task_name, task_type, owner_module, cron_expression, enabled, retry_times, "
                "timeout_seconds, config_json, running, created_at, updated_at) "
                "VALUES ('scan_watch_remove_rules', 'scheduled', 'signal', '0 20 * * *', 1, 0, "
                "300, :config_json, 0, :created_at, :updated_at)"
            ),
            {"config_json": config_json, "created_at": now, "updated_at": now},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM config_task WHERE task_name = 'scan_watch_remove_rules'")
    )
