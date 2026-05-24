from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.response import ok
from app.core.database import get_db
from app.models import (
    ConfigDataSource,
    ConfigDictionary,
    ConfigFieldMapping,
    ConfigNotificationTemplate,
    ConfigOperationLog,
    ConfigReviewTemplate,
    ConfigStrategy,
    ConfigTask,
    ConfigTaskLog,
    TradingRuleDefinition,
    TradingSystemDefinition,
    TradingSystemParamDefinition,
    TradingSystemRuleBinding,
    WatchPool,
    WatchSignal,
    WatchTrade,
    WatchTradeExecution,
)
from datetime import date

from app.services.prd_v1 import SeedService, record_operation
from app.services.tasks import TaskService

router = APIRouter(prefix="/admin", tags=["admin-prd-v1"])


def _mask_source(row: ConfigDataSource) -> dict:
    config = dict(row.config_json or {})
    for key in list(config):
        if "key" in key.lower() or "secret" in key.lower() or "password" in key.lower() or "token" in key.lower():
            config[key] = "***"
    return {
        "source_id": row.source_id,
        "source_name": row.source_name,
        "source_type": row.source_type,
        "platform": row.platform,
        "auth_type": row.auth_type,
        "base_url": row.base_url,
        "config_json": config,
        "enabled": row.enabled,
    }


def _trading_system_row(row: TradingSystemDefinition) -> dict:
    return {
        "system_id": row.system_id,
        "system_code": row.system_code,
        "system_name": row.system_name,
        "description": row.description,
        "lifecycle_desc": row.lifecycle_desc,
        "enabled": row.enabled,
        "sort_order": row.sort_order,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _trading_rule_row(row: TradingRuleDefinition) -> dict:
    return {
        "rule_id": row.rule_id,
        "rule_code": row.rule_code,
        "rule_name": row.rule_name,
        "rule_type": row.rule_type,
        "timeframe": row.timeframe,
        "executor_key": row.executor_key,
        "description": row.description,
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _trading_param_row(row: TradingSystemParamDefinition) -> dict:
    return {
        "param_id": row.param_id,
        "system_code": row.system_code,
        "param_key": row.param_key,
        "param_name": row.param_name,
        "param_type": row.param_type,
        "required": row.required,
        "default_value": row.default_value,
        "description": row.description,
        "sort_order": row.sort_order,
        "enabled": row.enabled,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _trading_binding_row(row: TradingSystemRuleBinding, rule: TradingRuleDefinition | None = None) -> dict:
    return {
        "binding_id": row.binding_id,
        "system_code": row.system_code,
        "rule_code": row.rule_code,
        "stage": row.stage,
        "required": row.required,
        "logic_group": row.logic_group,
        "logic_operator": row.logic_operator,
        "enabled": row.enabled,
        "sort_order": row.sort_order,
        "config_json": row.config_json or {},
        "rule": _trading_rule_row(rule) if rule else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _required_payload_text(payload: dict, key: str, label: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"{label} is required")
    return value


def _validate_choice(value: str, allowed: set[str], label: str) -> str:
    if value not in allowed:
        raise HTTPException(status_code=400, detail=f"{label} is invalid")
    return value


@router.get("/dashboard/overview")
def dashboard_overview(db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    return ok({
        "tasks": db.query(ConfigTask).count(),
        "data_sources": db.query(ConfigDataSource).count(),
        "dictionaries": db.query(ConfigDictionary).count(),
        "watch_count": db.query(WatchPool).count(),
        "signal_count": db.query(WatchSignal).count(),
        "trade_count": db.query(WatchTrade).count(),
    })


@router.get("/dashboard/task-summary")
def dashboard_task_summary(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return ok({"total": db.query(ConfigTask).count(), "running": db.query(ConfigTask).filter(ConfigTask.running.is_(True)).count()})


@router.get("/dashboard/data-source-summary")
def dashboard_data_source_summary(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return ok({"total": db.query(ConfigDataSource).count(), "enabled": db.query(ConfigDataSource).filter(ConfigDataSource.enabled.is_(True)).count()})


@router.get("/dashboard/error-top")
def dashboard_error_top(limit: int = 10, db: Session = Depends(get_db), admin=Depends(require_admin)):
    rows = db.query(ConfigTaskLog).filter(ConfigTaskLog.run_status == "failed").order_by(ConfigTaskLog.started_at.desc()).limit(limit).all()
    return ok([{"task_name": row.task_name, "error_message": row.error_message, "started_at": row.started_at} for row in rows])


@router.get("/data-sources")
def list_data_sources(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return ok([_mask_source(row) for row in db.query(ConfigDataSource).all()])


@router.post("/data-sources")
def create_data_source(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = ConfigDataSource(**{key: payload.get(key) for key in ["source_name", "source_type", "platform", "auth_type", "base_url", "config_json"] if key in payload})
    db.add(row)
    db.flush()
    record_operation(db, "create", "config_data_source", row.source_id, "新增数据源", payload)
    db.commit()
    return ok(_mask_source(row))


@router.get("/data-sources/{source_id}")
def get_data_source(source_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(ConfigDataSource).filter_by(source_id=source_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return ok(_mask_source(row))


@router.put("/data-sources/{source_id}")
def update_data_source(source_id: int, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(ConfigDataSource).filter_by(source_id=source_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    for key in ["source_name", "source_type", "platform", "auth_type", "base_url", "config_json", "enabled"]:
        if key in payload:
            setattr(row, key, payload[key])
    record_operation(db, "update", "config_data_source", source_id, "编辑数据源", payload)
    db.commit()
    return ok(_mask_source(row))


@router.post("/data-sources/{source_id}/enable")
def enable_data_source(source_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return update_data_source(source_id, {"enabled": True}, db, admin)


@router.post("/data-sources/{source_id}/disable")
def disable_data_source(source_id: int, payload: dict | None = None, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return update_data_source(source_id, {"enabled": False, "reason": (payload or {}).get("reason")}, db, admin)


@router.post("/data-sources/{source_id}/test")
def test_data_source(source_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(ConfigDataSource).filter_by(source_id=source_id).first()
    return ok({"source_id": source_id, "ok": bool(row), "message": "仅执行配置存在性测试，未连接未授权平台"})


@router.get("/data-sources/{source_id}/tasks")
def source_tasks(source_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return ok([{"task_id": row.task_id, "task_name": row.task_name, "enabled": row.enabled} for row in db.query(ConfigTask).all()])


@router.get("/data-sources/{source_id}/field-mappings")
def source_field_mappings(source_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return ok([
        {
            "mapping_id": row.mapping_id,
            "source_id": row.source_id,
            "platform": row.platform,
            "data_type": row.data_type,
            "raw_field_name": row.raw_field_name,
            "standard_field_name": row.standard_field_name,
            "enabled": row.enabled,
        }
        for row in db.query(ConfigFieldMapping).filter(ConfigFieldMapping.source_id == source_id).all()
    ])


@router.get("/tasks")
def list_tasks(db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    latest_logs: dict[str, ConfigTaskLog] = {}
    for log in db.query(ConfigTaskLog).order_by(ConfigTaskLog.started_at.desc()).limit(300).all():
        latest_logs.setdefault(log.task_name, log)
    return ok([
        {
            "task_id": row.task_id,
            "task_name": row.task_name,
            "task_type": row.task_type,
            "owner_module": row.owner_module,
            "enabled": row.enabled,
            "running": row.running,
            "retry_times": row.retry_times,
            "timeout_seconds": row.timeout_seconds,
            "config_json": row.config_json or {},
            "latest_run_status": latest_logs[row.task_name].run_status if row.task_name in latest_logs else None,
            "latest_started_at": latest_logs[row.task_name].started_at.isoformat() if row.task_name in latest_logs and latest_logs[row.task_name].started_at else None,
            "latest_finished_at": latest_logs[row.task_name].finished_at.isoformat() if row.task_name in latest_logs and latest_logs[row.task_name].finished_at else None,
            "latest_affected_rows": latest_logs[row.task_name].affected_rows if row.task_name in latest_logs else None,
            "latest_error_message": latest_logs[row.task_name].error_message if row.task_name in latest_logs else None,
        }
        for row in db.query(ConfigTask).order_by(ConfigTask.task_id.asc()).all()
    ])


@router.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(ConfigTask).filter_by(task_id=task_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return ok({"task_id": row.task_id, "task_name": row.task_name, "task_type": row.task_type, "enabled": row.enabled, "running": row.running, "config_json": row.config_json or {}})


@router.post("/tasks")
def create_task(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = ConfigTask(task_name=payload["task_name"], task_type=payload.get("task_type", "manual"), owner_module=payload.get("owner_module", ""), cron_expression=payload.get("cron_expression", ""), config_json=payload.get("config_json") or {})
    db.add(row)
    db.flush()
    record_operation(db, "create", "config_task", row.task_id, "新增任务", payload)
    db.commit()
    return ok({"task_id": row.task_id})


@router.put("/tasks/{task_id}")
def update_task(task_id: int, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(ConfigTask).filter_by(task_id=task_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    for key in ["cron_expression", "retry_times", "timeout_seconds", "enabled", "config_json"]:
        if key in payload:
            setattr(row, key, payload[key])
    record_operation(db, "update", "config_task", task_id, "编辑任务", payload)
    db.commit()
    return ok({"task_id": task_id})


@router.post("/tasks/{task_id}/run")
def run_config_task(task_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    task = db.query(ConfigTask).filter_by(task_id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    if task.running:
        raise HTTPException(status_code=409, detail="TASK_RUNNING")
    svc = TaskService(db)
    fn_map = {
        "collect_market_daily": svc.collect_market_daily,
        "collect_hot_sector_rank": svc.collect_hot_sector_rank,
        "collect_hot_stock_rank": svc.collect_hot_stock_rank,
        "collect_limit_up_daily": svc.collect_limit_up_daily,
        "update_watch_daily_kline": svc.update_watch_daily_kline,
        "update_watch_15m_kline": svc.update_watch_15m_kline,
        "prepare_watch_kline_data": svc.prepare_watch_kline_data,
        "prepare_trade_kline_data": svc.prepare_trade_kline_data,
        "update_watch_prices": svc.update_watch_prices,
        "scan_watch_signals": svc.scan_watch_signals,
        "scan_watch_rules": svc.scan_watch_rules,
        "scan_trade_rules": svc.scan_trade_rules,
        "auto_remove_watch_pool": svc.auto_remove_watch_pool,
        "scan_trade_risk_signals": svc.scan_trade_risk_signals,
        "generate_weekly_review_form": svc.generate_weekly_review_form,
        "generate_monthly_review_form": svc.generate_monthly_review_form,
        "remind_pending_review_form": svc.remind_pending_review_form,
        "aggregate_review_metrics": svc.aggregate_review_metrics,
    }
    fn = fn_map.get(task.task_name)
    if fn is None:
        raise HTTPException(status_code=400, detail=f"UNKNOWN_TASK: {task.task_name}")
    log = fn(date.today())
    return ok({"task_name": task.task_name, "run_status": log.run_status, "affected_rows": log.affected_rows})


@router.post("/tasks/{task_id}/enable")
def enable_task(task_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return update_task(task_id, {"enabled": True}, db, admin)


@router.post("/tasks/{task_id}/disable")
def disable_task(task_id: int, payload: dict | None = None, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return update_task(task_id, {"enabled": False, "reason": (payload or {}).get("reason")}, db, admin)


@router.post("/tasks/{task_id}/rerun")
def rerun_task(task_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return run_config_task(task_id, db, admin)


@router.get("/tasks/{task_id}/logs")
def task_logs(task_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return ok([{"log_id": row.log_id, "task_name": row.task_name, "run_status": row.run_status, "started_at": row.started_at, "finished_at": row.finished_at, "affected_rows": row.affected_rows, "error_message": row.error_message} for row in db.query(ConfigTaskLog).filter(ConfigTaskLog.task_id == task_id).order_by(ConfigTaskLog.started_at.desc()).all()])


@router.get("/task-logs")
def all_task_logs(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return ok([{"log_id": row.log_id, "task_name": row.task_name, "run_status": row.run_status, "started_at": row.started_at, "finished_at": row.finished_at, "affected_rows": row.affected_rows, "error_message": row.error_message} for row in db.query(ConfigTaskLog).order_by(ConfigTaskLog.started_at.desc()).limit(100).all()])


@router.get("/dictionaries")
def list_dictionaries(dict_type: str | None = None, db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    query = db.query(ConfigDictionary)
    if dict_type:
        query = query.filter(ConfigDictionary.dict_type == dict_type)
    return ok([{"dict_id": row.dict_id, "dict_type": row.dict_type, "dict_label": row.dict_label, "dict_value": row.dict_value, "enabled": row.enabled} for row in query.order_by(ConfigDictionary.dict_type, ConfigDictionary.sort_order).all()])


@router.post("/dictionaries")
def create_dictionary(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = ConfigDictionary(dict_type=payload["dict_type"], dict_label=payload["dict_label"], dict_value=payload.get("dict_value", payload["dict_label"]), sort_order=payload.get("sort_order", 0))
    db.add(row)
    db.flush()
    record_operation(db, "create", "config_dictionary", row.dict_id, "新增字典", payload)
    db.commit()
    return ok({"dict_id": row.dict_id})


@router.put("/dictionaries/{dict_id}")
def update_dictionary(dict_id: int, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(ConfigDictionary).filter_by(dict_id=dict_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    for key in ["dict_label", "dict_value", "sort_order", "enabled", "description"]:
        if key in payload:
            setattr(row, key, payload[key])
    record_operation(db, "update", "config_dictionary", dict_id, "编辑字典", payload)
    db.commit()
    return ok({"dict_id": dict_id})


@router.post("/dictionaries/{dict_id}/enable")
def enable_dictionary(dict_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return update_dictionary(dict_id, {"enabled": True}, db, admin)


@router.post("/dictionaries/{dict_id}/disable")
def disable_dictionary(dict_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    return update_dictionary(dict_id, {"enabled": False}, db, admin)


@router.post("/dictionaries/reorder")
def reorder_dictionaries(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    for order, dict_id in enumerate(payload.get("ordered_ids", []), start=1):
        row = db.query(ConfigDictionary).filter_by(dict_id=dict_id).first()
        if row:
            row.sort_order = order
    db.commit()
    return ok({"reordered": True})


@router.get("/dictionaries/types")
def dictionary_types(db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    return ok([row[0] for row in db.query(ConfigDictionary.dict_type).distinct().all()])


@router.get("/field-mappings")
def list_field_mappings(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return ok([{"mapping_id": row.mapping_id, "data_type": row.data_type, "raw_field_name": row.raw_field_name, "standard_field_name": row.standard_field_name, "enabled": row.enabled} for row in db.query(ConfigFieldMapping).all()])


@router.post("/field-mappings")
def create_field_mapping(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = ConfigFieldMapping(**payload)
    db.add(row)
    db.flush()
    record_operation(db, "create", "config_field_mapping", row.mapping_id, "新增字段映射", payload)
    db.commit()
    return ok({"mapping_id": row.mapping_id})


@router.put("/field-mappings/{mapping_id}")
def update_field_mapping(mapping_id: int, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(ConfigFieldMapping).filter_by(mapping_id=mapping_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    for key, value in payload.items():
        if hasattr(row, key):
            setattr(row, key, value)
    record_operation(db, "update", "config_field_mapping", mapping_id, "编辑字段映射", payload)
    db.commit()
    return ok({"mapping_id": mapping_id})


@router.post("/field-mappings/validate")
def validate_field_mapping(payload: dict, admin=Depends(require_admin)):
    required = ["raw_field_name", "standard_field_name"]
    return ok({"valid": all(key in payload for key in required), "required": required})


@router.get("/strategies")
def list_strategies(db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    return ok([{"strategy_id": row.strategy_id, "strategy_name": row.strategy_name, "strategy_type": row.strategy_type, "enabled": row.enabled} for row in db.query(ConfigStrategy).all()])


@router.get("/strategies/defaults")
def strategy_defaults(db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    return list_strategies(db, admin)


@router.get("/trading-systems")
def list_trading_systems(db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    rows = db.query(TradingSystemDefinition).order_by(TradingSystemDefinition.sort_order.asc(), TradingSystemDefinition.system_id.asc()).all()
    return ok([_trading_system_row(row) for row in rows])


@router.post("/trading-systems")
def create_trading_system(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    system_code = _required_payload_text(payload, "system_code", "system_code")
    system_name = _required_payload_text(payload, "system_name", "system_name")
    if db.query(TradingSystemDefinition).filter(TradingSystemDefinition.system_code == system_code).first():
        raise HTTPException(status_code=409, detail="system_code already exists")
    row = TradingSystemDefinition(
        system_code=system_code,
        system_name=system_name,
        description=payload.get("description") or "",
        lifecycle_desc=payload.get("lifecycle_desc") or "",
        enabled=bool(payload.get("enabled", True)),
        sort_order=int(payload.get("sort_order") or 0),
    )
    db.add(row)
    db.flush()
    record_operation(db, "create", "trading_system_definition", row.system_id, "新增交易体系", payload)
    db.commit()
    db.refresh(row)
    return ok(_trading_system_row(row))


@router.get("/trading-systems/{system_code}")
def get_trading_system(system_code: str, db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    row = db.query(TradingSystemDefinition).filter(TradingSystemDefinition.system_code == system_code).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return ok(_trading_system_row(row))


@router.put("/trading-systems/{system_code}")
def update_trading_system(system_code: str, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(TradingSystemDefinition).filter(TradingSystemDefinition.system_code == system_code).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    for key in ["system_name", "description", "lifecycle_desc", "enabled", "sort_order"]:
        if key in payload:
            setattr(row, key, payload[key])
    record_operation(db, "update", "trading_system_definition", row.system_id, "编辑交易体系", payload)
    db.commit()
    db.refresh(row)
    return ok(_trading_system_row(row))


@router.get("/trading-executors")
def list_trading_executors(admin=Depends(require_admin)):
    from app.rule_executors import list_executors

    return ok(list_executors())


@router.get("/trading-rules")
def list_trading_rules(db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    rows = db.query(TradingRuleDefinition).order_by(TradingRuleDefinition.rule_type.asc(), TradingRuleDefinition.rule_id.asc()).all()
    return ok([_trading_rule_row(row) for row in rows])


@router.post("/trading-rules")
def create_trading_rule(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    rule_code = _required_payload_text(payload, "rule_code", "rule_code")
    rule_name = _required_payload_text(payload, "rule_name", "rule_name")
    rule_type = _validate_choice(_required_payload_text(payload, "rule_type", "rule_type"), {"buy_signal", "sell_signal", "stop_loss", "filter", "confirm"}, "rule_type")
    timeframe = _validate_choice(_required_payload_text(payload, "timeframe", "timeframe"), {"5m", "15m", "30m", "daily"}, "timeframe")
    executor_key = _required_payload_text(payload, "executor_key", "executor_key")
    if db.query(TradingRuleDefinition).filter(TradingRuleDefinition.rule_code == rule_code).first():
        raise HTTPException(status_code=409, detail="rule_code already exists")
    row = TradingRuleDefinition(
        rule_code=rule_code,
        rule_name=rule_name,
        rule_type=rule_type,
        timeframe=timeframe,
        executor_key=executor_key,
        description=payload.get("description") or "",
        enabled=bool(payload.get("enabled", True)),
    )
    db.add(row)
    db.flush()
    record_operation(db, "create", "trading_rule_definition", row.rule_id, "新增交易规则", payload)
    db.commit()
    db.refresh(row)
    return ok(_trading_rule_row(row))


@router.put("/trading-rules/{rule_code}")
def update_trading_rule(rule_code: str, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(TradingRuleDefinition).filter(TradingRuleDefinition.rule_code == rule_code).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    if "rule_name" in payload:
        row.rule_name = _required_payload_text(payload, "rule_name", "rule_name")
    if "rule_type" in payload:
        row.rule_type = _validate_choice(str(payload["rule_type"]), {"buy_signal", "sell_signal", "stop_loss", "filter", "confirm"}, "rule_type")
    if "timeframe" in payload:
        row.timeframe = _validate_choice(str(payload["timeframe"]), {"5m", "15m", "30m", "daily"}, "timeframe")
    for key in ["executor_key", "description", "enabled"]:
        if key in payload:
            setattr(row, key, payload[key])
    record_operation(db, "update", "trading_rule_definition", row.rule_id, "编辑交易规则", payload)
    db.commit()
    db.refresh(row)
    return ok(_trading_rule_row(row))


@router.get("/trading-systems/{system_code}/params")
def list_trading_system_params(system_code: str, db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    rows = (
        db.query(TradingSystemParamDefinition)
        .filter(TradingSystemParamDefinition.system_code == system_code)
        .order_by(TradingSystemParamDefinition.sort_order.asc(), TradingSystemParamDefinition.param_id.asc())
        .all()
    )
    return ok([_trading_param_row(row) for row in rows])


@router.post("/trading-systems/{system_code}/params")
def create_trading_system_param(system_code: str, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if not db.query(TradingSystemDefinition).filter(TradingSystemDefinition.system_code == system_code).first():
        raise HTTPException(status_code=404, detail="SYSTEM_NOT_FOUND")
    param_key = _required_payload_text(payload, "param_key", "param_key")
    param_name = _required_payload_text(payload, "param_name", "param_name")
    param_type = _validate_choice(_required_payload_text(payload, "param_type", "param_type"), {"number", "text", "select", "boolean"}, "param_type")
    if db.query(TradingSystemParamDefinition).filter_by(system_code=system_code, param_key=param_key).first():
        raise HTTPException(status_code=409, detail="param_key already exists")
    row = TradingSystemParamDefinition(
        system_code=system_code,
        param_key=param_key,
        param_name=param_name,
        param_type=param_type,
        required=bool(payload.get("required", False)),
        default_value=payload.get("default_value"),
        description=payload.get("description") or "",
        sort_order=int(payload.get("sort_order") or 0),
        enabled=bool(payload.get("enabled", True)),
    )
    db.add(row)
    db.flush()
    record_operation(db, "create", "trading_system_param_definition", row.param_id, "新增交易体系参数", payload)
    db.commit()
    db.refresh(row)
    return ok(_trading_param_row(row))


@router.put("/trading-params/{param_id}")
def update_trading_system_param(param_id: int, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(TradingSystemParamDefinition).filter(TradingSystemParamDefinition.param_id == param_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    if "param_name" in payload:
        row.param_name = _required_payload_text(payload, "param_name", "param_name")
    if "param_type" in payload:
        row.param_type = _validate_choice(str(payload["param_type"]), {"number", "text", "select", "boolean"}, "param_type")
    for key in ["required", "default_value", "description", "sort_order", "enabled"]:
        if key in payload:
            setattr(row, key, payload[key])
    record_operation(db, "update", "trading_system_param_definition", row.param_id, "编辑交易体系参数", payload)
    db.commit()
    db.refresh(row)
    return ok(_trading_param_row(row))


@router.get("/trading-systems/{system_code}/rules")
def list_trading_system_rules(system_code: str, db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    rows = (
        db.query(TradingSystemRuleBinding, TradingRuleDefinition)
        .outerjoin(TradingRuleDefinition, TradingRuleDefinition.rule_code == TradingSystemRuleBinding.rule_code)
        .filter(TradingSystemRuleBinding.system_code == system_code)
        .order_by(TradingSystemRuleBinding.stage.asc(), TradingSystemRuleBinding.sort_order.asc(), TradingSystemRuleBinding.binding_id.asc())
        .all()
    )
    return ok([_trading_binding_row(binding, rule) for binding, rule in rows])


@router.post("/trading-systems/{system_code}/rules")
def create_trading_system_rule_binding(system_code: str, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    if not db.query(TradingSystemDefinition).filter(TradingSystemDefinition.system_code == system_code).first():
        raise HTTPException(status_code=404, detail="SYSTEM_NOT_FOUND")
    rule_code = _required_payload_text(payload, "rule_code", "rule_code")
    if not db.query(TradingRuleDefinition).filter(TradingRuleDefinition.rule_code == rule_code).first():
        raise HTTPException(status_code=404, detail="RULE_NOT_FOUND")
    stage = _validate_choice(_required_payload_text(payload, "stage", "stage"), {"observe", "buy_confirm", "trading", "sell", "stop_loss"}, "stage")
    if db.query(TradingSystemRuleBinding).filter_by(system_code=system_code, rule_code=rule_code, stage=stage).first():
        raise HTTPException(status_code=409, detail="binding already exists")
    row = TradingSystemRuleBinding(
        system_code=system_code,
        rule_code=rule_code,
        stage=stage,
        required=bool(payload.get("required", False)),
        logic_group=payload.get("logic_group") or "",
        logic_operator=_validate_choice(str(payload.get("logic_operator") or "AND"), {"AND", "OR"}, "logic_operator"),
        enabled=bool(payload.get("enabled", True)),
        sort_order=int(payload.get("sort_order") or 0),
        config_json=payload.get("config_json") or {},
    )
    db.add(row)
    db.flush()
    record_operation(db, "create", "trading_system_rule_binding", row.binding_id, "新增体系规则绑定", payload)
    db.commit()
    rule = db.query(TradingRuleDefinition).filter(TradingRuleDefinition.rule_code == row.rule_code).first()
    return ok(_trading_binding_row(row, rule))


@router.put("/trading-rule-bindings/{binding_id}")
def update_trading_system_rule_binding(binding_id: int, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(TradingSystemRuleBinding).filter(TradingSystemRuleBinding.binding_id == binding_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    if "rule_code" in payload:
        rule_code = _required_payload_text(payload, "rule_code", "rule_code")
        if not db.query(TradingRuleDefinition).filter(TradingRuleDefinition.rule_code == rule_code).first():
            raise HTTPException(status_code=404, detail="RULE_NOT_FOUND")
        row.rule_code = rule_code
    if "stage" in payload:
        row.stage = _validate_choice(str(payload["stage"]), {"observe", "buy_confirm", "trading", "sell", "stop_loss"}, "stage")
    if "logic_operator" in payload:
        row.logic_operator = _validate_choice(str(payload["logic_operator"]), {"AND", "OR"}, "logic_operator")
    for key in ["required", "logic_group", "enabled", "sort_order", "config_json"]:
        if key in payload:
            setattr(row, key, payload[key])
    record_operation(db, "update", "trading_system_rule_binding", row.binding_id, "编辑体系规则绑定", payload)
    db.commit()
    rule = db.query(TradingRuleDefinition).filter(TradingRuleDefinition.rule_code == row.rule_code).first()
    return ok(_trading_binding_row(row, rule))


@router.get("/logs/operations")
def operation_logs(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return ok([{"log_id": row.log_id, "operation_type": row.operation_type, "target_type": row.target_type, "summary": row.summary, "created_at": row.created_at} for row in db.query(ConfigOperationLog).order_by(ConfigOperationLog.created_at.desc()).limit(100).all()])


@router.get("/notification-templates")
def notification_templates(db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    return ok([{"template_id": row.template_id, "push_type": row.push_type, "channel": row.channel, "enabled": row.enabled} for row in db.query(ConfigNotificationTemplate).all()])


@router.get("/review-templates")
def review_templates(db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    return ok([{"template_id": row.template_id, "review_type": row.review_type, "template_name": row.template_name, "enabled": row.enabled} for row in db.query(ConfigReviewTemplate).all()])


@router.get("/account/profile")
def admin_profile(admin=Depends(require_admin)):
    return ok({"user_id": "single-user", "nickname": "Aquant 管理员"})


@router.get("/security/sensitive-summary")
def sensitive_summary(admin=Depends(require_admin)):
    return ok({"database_url": "***", "redis_url": "***", "data_source_auth": "***"})


@router.post("/market/collect-all")
def collect_all_market_data(db: Session = Depends(get_db), admin=Depends(require_admin)):
    svc = TaskService(db)
    today = date.today()
    results = {}
    for task_name, fn in [
        ("collect_market_daily", svc.collect_market_daily),
        ("collect_hot_sector_rank", svc.collect_hot_sector_rank),
        ("collect_hot_stock_rank", svc.collect_hot_stock_rank),
        ("collect_limit_up_daily", svc.collect_limit_up_daily),
    ]:
        log = fn(today)
        results[task_name] = {"status": log.run_status, "affected_rows": log.affected_rows}
    return ok({"collect_time": datetime.utcnow().isoformat(), "results": results})


# ── Admin Watch / Signal / Trade Management ──────────────────────────


def _watch_row(row):
    return {
        "watch_id": row.id, "stock_code": row.stock_code, "stock_name": row.stock_name,
        "status": row.status, "trading_system": row.trading_system,
        "trading_system_code": row.trading_system_code,
        "system_stage": row.system_stage or "observe",
        "system_params_json": row.system_params_json or {},
        "active_rule_codes_json": row.active_rule_codes_json or [],
        "next_action": row.next_action,
        "key_observe_price": row.key_observe_price, "auto_remove_price": row.auto_remove_price,
        "invalid_condition": row.invalid_condition, "entry_reason": row.entry_reason,
        "monitor_enabled": row.monitor_enabled, "signal_enabled": row.signal_enabled,
        "latest_signal_id": row.latest_signal_id, "active": row.active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _signal_row(row):
    return {
        "signal_id": row.signal_id, "watch_id": row.watch_id,
        "stock_code": row.stock_code, "stock_name": row.stock_name,
        "signal_type": row.signal_type, "buy_point_type": row.buy_point_type,
        "trading_system_code": row.trading_system_code,
        "rule_code": row.rule_code,
        "rule_type": row.rule_type,
        "strategy_name": row.strategy_name, "signal_level": row.signal_level,
        "signal_status": row.signal_status, "trading_system": row.trading_system,
        "trigger_price": row.trigger_price, "trigger_time": row.trigger_time.isoformat() if row.trigger_time else None,
        "trigger_date": row.trigger_date.isoformat() if row.trigger_date else None,
        "stop_loss_price": row.stop_loss_price, "target_price": row.target_price,
        "trigger_reason": row.trigger_reason, "risk_desc": row.risk_desc,
        "buy_point_confirmed": row.buy_point_confirmed,
        "buy_point_confirm_time": row.buy_point_confirm_time.isoformat() if row.buy_point_confirm_time else None,
        "buy_point_confirm_price": row.buy_point_confirm_price,
        "user_action": row.user_action, "related_trade_id": row.related_trade_id,
        "snapshot_json": row.snapshot_json or row.raw_snapshot or {},
        "notification_sent": row.notification_sent,
        "notification_sent_at": row.notification_sent_at.isoformat() if row.notification_sent_at else None,
        "notification_error": row.notification_error,
    }


def _trade_row(row):
    return {
        "trade_id": row.id, "signal_id": row.signal_id, "watch_id": row.watch_id,
        "stock_code": row.stock_code, "stock_name": row.stock_name,
        "trading_system": row.trading_system, "buy_point_type": row.buy_point_type,
        "trading_system_code": row.trading_system_code,
        "entry_rule_code": row.entry_rule_code,
        "system_params_json": row.system_params_json or {},
        "active_sell_rule_codes_json": row.active_sell_rule_codes_json or [],
        "active_stop_rule_codes_json": row.active_stop_rule_codes_json or [],
        "current_stage": row.current_stage or "trading",
        "latest_trade_signal_id": row.latest_trade_signal_id,
        "first_buy_price": row.first_buy_price, "total_buy_amount": row.total_buy_amount,
        "average_buy_price": row.average_buy_price, "remaining_amount": row.remaining_amount,
        "position_ratio": row.position_ratio, "stop_loss_price": row.stop_loss_price,
        "target_price": row.target_price, "trade_status": row.trade_status,
        "pnl_amount": row.pnl_amount, "pnl_ratio": row.pnl_ratio, "holding_days": row.holding_days,
    }


def _required_text(payload: dict, key: str, label: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail=f"{label}不能为空")
    return value


def _optional_positive_float(payload: dict, key: str, label: str) -> float | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{label}必须是数字") from exc
    if number <= 0:
        raise HTTPException(status_code=400, detail=f"{label}必须大于0")
    return number


def _required_positive_float(payload: dict, key: str, label: str) -> float:
    value = _optional_positive_float(payload, key, label)
    if value is None:
        raise HTTPException(status_code=400, detail=f"{label}不能为空")
    return value


# ── Watch Pool ──

@router.get("/watch-pool")
def admin_list_watch(status: str | None = None, keyword: str | None = None, db: Session = Depends(get_db), admin=Depends(require_admin)):
    query = db.query(WatchPool)
    if status:
        query = query.filter(WatchPool.status == status)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter(or_(WatchPool.stock_code.ilike(like), WatchPool.stock_name.ilike(like)))
    rows = query.order_by(WatchPool.id.desc()).limit(200).all()
    return ok([_watch_row(r) for r in rows])


@router.post("/watch-pool")
def admin_add_watch(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    from app.services.prd_v1 import PrdWatchPoolService
    from app.services.normalization import normalize_stock_code
    code = normalize_stock_code(_required_text(payload, "stock_code", "股票代码"))
    stock_name = _required_text(payload, "stock_name", "股票名称")
    invalid_condition = _required_text(payload, "invalid_condition", "失效条件")
    key_observe_price = _required_positive_float(payload, "key_observe_price", "观察价")
    auto_remove_price = _optional_positive_float(payload, "auto_remove_price", "自动剔除价")
    existing = db.query(WatchPool).filter(WatchPool.stock_code == code, WatchPool.active.is_(True)).first()
    if existing:
        raise HTTPException(status_code=409, detail="该股票已在观察池中")
    svc = PrdWatchPoolService(db)
    try:
        row = svc.add_watch({
            "stock_code": code,
            "stock_name": stock_name,
            "trading_system": payload.get("trading_system", "uptrend"),
            "trading_system_code": payload.get("trading_system_code"),
            "system_params_json": payload.get("system_params_json"),
            "system_stage": payload.get("system_stage", "observe"),
            "entry_reason": payload.get("entry_reason", "后台手动添加"),
            "reason": payload.get("entry_reason", "后台手动添加"),
            "key_observe_price": key_observe_price,
            "auto_remove_price": auto_remove_price,
            "invalid_condition": invalid_condition,
            "labels": payload.get("labels", ["manual"]),
        })
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(_watch_row(row))


# ── Signals ──

@router.get("/watch-signals")
def admin_list_signals(db: Session = Depends(get_db), admin=Depends(require_admin)):
    rows = db.query(WatchSignal).order_by(WatchSignal.signal_id.desc()).limit(100).all()
    return ok([_signal_row(r) for r in rows])


@router.get("/watch-pool/{watch_id}/signals")
def admin_watch_signals(watch_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    rows = db.query(WatchSignal).filter(WatchSignal.watch_id == watch_id).order_by(WatchSignal.signal_id.desc()).all()
    return ok([_signal_row(r) for r in rows])


@router.post("/watch-pool/{watch_id}/signals")
def admin_add_signal(watch_id: int, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    watch = db.query(WatchPool).filter(WatchPool.id == watch_id).first()
    if not watch:
        raise HTTPException(status_code=404, detail="watch not found")

    now = datetime.utcnow()
    buy_confirmed = payload.get("buy_point_confirmed", False)
    signal_type = payload.get("signal_type", "buy")
    buy_point_type = payload.get("buy_point_type") or "b15_divergence"
    trigger_price = _optional_positive_float(payload, "trigger_price", "触发价")
    stop_loss_price = _optional_positive_float(payload, "stop_loss_price", "止损价")
    target_price = _optional_positive_float(payload, "target_price", "目标价")
    trigger_signature = payload.get("trigger_signature") or f"admin:{watch_id}:{payload.get('strategy_name', 'manual')}:{now.isoformat()}"
    existing = db.query(WatchSignal).filter(
        WatchSignal.stock_code == watch.stock_code,
        WatchSignal.buy_point_type == buy_point_type,
        WatchSignal.signal_type == signal_type,
        WatchSignal.trigger_date == now.date(),
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="该股票今日已存在相同买点信号")

    signal = WatchSignal(
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        signal_type=signal_type,
        buy_point_type=buy_point_type,
        strategy_name=payload.get("strategy_name", "manual_admin_signal"),
        signal_level=payload.get("signal_level", "A"),
        trading_system=watch.trading_system,
        trigger_time=now,
        trigger_date=now.date(),
        trigger_price=trigger_price,
        trigger_reason=payload.get("trigger_reason", "后台手动添加信号"),
        risk_desc=payload.get("risk_desc", "仅作为交易辅助"),
        stop_loss_price=stop_loss_price,
        target_price=target_price,
        buy_point_confirmed=buy_confirmed,
        buy_point_confirm_time=now if buy_confirmed else None,
        buy_point_confirm_price=(trigger_price if buy_confirmed else None),
        signal_status="buy_pending_confirm" if buy_confirmed else "signal_generated",
        user_action="pending",
        trigger_signature=trigger_signature,
        raw_snapshot={},
    )
    db.add(signal)
    db.flush()

    watch.status = "buy_pending_confirm" if buy_confirmed else "signal_generated"
    watch.latest_signal_id = signal.signal_id
    db.commit()
    db.refresh(signal)
    return ok(_signal_row(signal))


# ── Trades ──

@router.get("/watch-trades")
def admin_list_trades(db: Session = Depends(get_db), admin=Depends(require_admin)):
    rows = db.query(WatchTrade).order_by(WatchTrade.id.desc()).limit(100).all()
    return ok([_trade_row(r) for r in rows])


@router.post("/watch-signals/{signal_id}/create-trade")
def admin_create_trade(signal_id: int, payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    from app.services.trade_context import apply_confirm_buy_trade_context

    signal = db.query(WatchSignal).filter(WatchSignal.signal_id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="signal not found")

    existing = db.query(WatchTrade).filter(WatchTrade.signal_id == signal_id).first()
    if existing:
        watch = db.query(WatchPool).filter(WatchPool.id == signal.watch_id).first() if signal.watch_id else None
        apply_confirm_buy_trade_context(db, existing, signal, watch)
        db.commit()
        return ok(_trade_row(existing), message="signal already has a trade")

    now = datetime.utcnow()
    buy_price = _required_positive_float(payload, "buy_price", "买入价")
    amount = _required_positive_float(payload, "amount", "数量")
    position_ratio = _optional_positive_float(payload, "position_ratio", "仓位")
    stop_loss_price = _optional_positive_float(payload, "stop_loss_price", "止损价")
    target_price = _optional_positive_float(payload, "target_price", "目标价")

    watch = db.query(WatchPool).filter(WatchPool.id == signal.watch_id).first() if signal.watch_id else None
    trade = WatchTrade(
        signal_id=signal.signal_id,
        watch_id=signal.watch_id,
        stock_code=signal.stock_code,
        stock_name=signal.stock_name,
        trading_system=signal.trading_system,
        trading_system_code=signal.trading_system_code or (watch.trading_system_code if watch else None),
        entry_rule_code=signal.rule_code or signal.buy_point_type,
        buy_point_type=signal.buy_point_type,
        first_buy_time=now,
        first_buy_price=buy_price,
        total_buy_amount=amount,
        average_buy_price=buy_price,
        remaining_amount=amount,
        position_ratio=position_ratio,
        stop_loss_price=stop_loss_price,
        target_price=target_price,
        buy_reason=payload.get("buy_reason", "后台手动确认交易"),
        trade_plan=payload.get("trade_plan", ""),
        trade_status="open",
    )
    db.add(trade)
    db.flush()
    apply_confirm_buy_trade_context(db, trade, signal, watch)

    db.add(WatchTradeExecution(
        trade_id=trade.id, signal_id=signal.signal_id, watch_id=signal.watch_id,
        stock_code=signal.stock_code, stock_name=signal.stock_name,
        execution_type="buy", execution_time=now, execution_price=buy_price,
        execution_amount=amount, execution_reason=payload.get("buy_reason", "后台手动确认交易"),
    ))

    signal.signal_status = "confirmed_buy"
    signal.user_action = "confirmed_buy"
    signal.handled_at = now
    signal.related_trade_id = trade.id
    signal.buy_point_confirmed = True
    signal.buy_point_confirm_time = signal.buy_point_confirm_time or now
    signal.buy_point_confirm_price = signal.buy_point_confirm_price or buy_price

    if watch:
        watch.status = "trading"
        watch.system_stage = "trading"
        watch.monitor_enabled = False
        watch.signal_enabled = False

    db.commit()
    db.refresh(trade)
    return ok(_trade_row(trade))
