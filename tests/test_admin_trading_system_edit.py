from datetime import datetime

from app.models import ConfigTaskLog


def test_admin_can_create_and_edit_trading_system(client):
    created = client.post(
        "/api/admin/trading-systems",
        json={
            "system_code": "admin_edit_system",
            "system_name": "后台编辑体系",
            "description": "created from admin",
            "lifecycle_desc": "observe to trade",
            "enabled": True,
            "sort_order": 90,
        },
    )
    assert created.status_code == 200
    assert created.json()["data"]["system_code"] == "admin_edit_system"

    updated = client.put(
        "/api/admin/trading-systems/admin_edit_system",
        json={"system_name": "后台编辑体系 v2", "description": "updated", "enabled": False},
    )
    assert updated.status_code == 200
    payload = updated.json()["data"]
    assert payload["system_name"] == "后台编辑体系 v2"
    assert payload["enabled"] is False


def test_admin_can_manage_rule_param_and_binding(client):
    client.post(
        "/api/admin/trading-systems",
        json={"system_code": "binding_system", "system_name": "绑定测试体系", "enabled": True},
    )

    executors = client.get("/api/admin/trading-executors")
    assert executors.status_code == 200
    assert "always_false" in executors.json()["data"]

    rule = client.post(
        "/api/admin/trading-rules",
        json={
            "rule_code": "admin_rule_missing_executor",
            "rule_name": "无执行器提示规则",
            "rule_type": "buy_signal",
            "timeframe": "15m",
            "executor_key": "missing_executor_for_admin_warning",
            "enabled": True,
        },
    )
    assert rule.status_code == 200
    assert rule.json()["data"]["executor_key"] == "missing_executor_for_admin_warning"

    rule_updated = client.put(
        "/api/admin/trading-rules/admin_rule_missing_executor",
        json={"rule_name": "无执行器提示规则 v2", "timeframe": "5m", "enabled": False},
    )
    assert rule_updated.status_code == 200
    assert rule_updated.json()["data"]["timeframe"] == "5m"
    assert rule_updated.json()["data"]["enabled"] is False

    param = client.post(
        "/api/admin/trading-systems/binding_system/params",
        json={
            "param_key": "observe_price",
            "param_name": "观察价",
            "param_type": "number",
            "required": True,
            "sort_order": 1,
            "enabled": True,
        },
    )
    assert param.status_code == 200
    param_id = param.json()["data"]["param_id"]

    param_updated = client.put(
        f"/api/admin/trading-params/{param_id}",
        json={"param_name": "核心观察价", "required": False, "sort_order": 2},
    )
    assert param_updated.status_code == 200
    assert param_updated.json()["data"]["required"] is False
    assert param_updated.json()["data"]["sort_order"] == 2

    binding = client.post(
        "/api/admin/trading-systems/binding_system/rules",
        json={
            "rule_code": "admin_rule_missing_executor",
            "stage": "observe",
            "required": True,
            "logic_group": "entry",
            "logic_operator": "AND",
            "enabled": True,
            "sort_order": 1,
        },
    )
    assert binding.status_code == 200
    binding_id = binding.json()["data"]["binding_id"]

    binding_updated = client.put(
        f"/api/admin/trading-rule-bindings/{binding_id}",
        json={"stage": "trading", "required": False, "logic_operator": "OR", "enabled": False},
    )
    assert binding_updated.status_code == 200
    data = binding_updated.json()["data"]
    assert data["stage"] == "trading"
    assert data["logic_operator"] == "OR"
    assert data["enabled"] is False


def test_admin_tasks_include_latest_run_summary(client, db_session):
    response = client.get("/api/admin/tasks")
    assert response.status_code == 200
    task = next(item for item in response.json()["data"] if item["task_name"] == "scan_watch_rules")
    db_session.add(
        ConfigTaskLog(
            task_id=task["task_id"],
            task_name="scan_watch_rules",
            run_status="success",
            started_at=datetime(2026, 5, 24, 10, 0),
            finished_at=datetime(2026, 5, 24, 10, 1),
            affected_rows=3,
            error_message="",
        )
    )
    db_session.commit()

    refreshed = client.get("/api/admin/tasks")
    assert refreshed.status_code == 200
    payload = next(item for item in refreshed.json()["data"] if item["task_name"] == "scan_watch_rules")
    assert payload["owner_module"] == "signal"
    assert payload["latest_run_status"] == "success"
    assert payload["latest_affected_rows"] == 3
    assert payload["latest_started_at"].startswith("2026-05-24T10:00:00")
