from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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


@router.get("/dashboard/overview")
def dashboard_overview(db: Session = Depends(get_db), admin=Depends(require_admin)):
    SeedService(db).init_defaults()
    return ok({"tasks": db.query(ConfigTask).count(), "data_sources": db.query(ConfigDataSource).count(), "dictionaries": db.query(ConfigDictionary).count()})


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
    return ok([{"task_id": row.task_id, "task_name": row.task_name, "task_type": row.task_type, "enabled": row.enabled, "running": row.running} for row in db.query(ConfigTask).all()])


@router.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = db.query(ConfigTask).filter_by(task_id=task_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return ok({"task_id": row.task_id, "task_name": row.task_name, "task_type": row.task_type, "enabled": row.enabled, "running": row.running})


@router.post("/tasks")
def create_task(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    row = ConfigTask(task_name=payload["task_name"], task_type=payload.get("task_type", "manual"), owner_module=payload.get("owner_module", ""), cron_expression=payload.get("cron_expression", ""))
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
    for key in ["cron_expression", "retry_times", "timeout_seconds", "enabled"]:
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
        "scan_watch_signals": svc.scan_watch_signals,
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
    return ok([{"log_id": row.log_id, "task_name": row.task_name, "run_status": row.run_status, "error_message": row.error_message} for row in db.query(ConfigTaskLog).filter(ConfigTaskLog.task_id == task_id).order_by(ConfigTaskLog.started_at.desc()).all()])


@router.get("/task-logs")
def all_task_logs(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return ok([{"log_id": row.log_id, "task_name": row.task_name, "run_status": row.run_status, "error_message": row.error_message} for row in db.query(ConfigTaskLog).order_by(ConfigTaskLog.started_at.desc()).limit(100).all()])


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
        "key_observe_price": row.key_observe_price, "auto_remove_price": row.auto_remove_price,
        "invalid_condition": row.invalid_condition, "entry_reason": row.entry_reason,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _signal_row(row):
    return {
        "signal_id": row.signal_id, "watch_id": row.watch_id,
        "stock_code": row.stock_code, "stock_name": row.stock_name,
        "signal_type": row.signal_type, "buy_point_type": row.buy_point_type,
        "strategy_name": row.strategy_name, "signal_level": row.signal_level,
        "signal_status": row.signal_status, "trading_system": row.trading_system,
        "trigger_price": row.trigger_price, "trigger_time": row.trigger_time.isoformat() if row.trigger_time else None,
        "stop_loss_price": row.stop_loss_price, "target_price": row.target_price,
        "trigger_reason": row.trigger_reason, "risk_desc": row.risk_desc,
    }


def _trade_row(row):
    return {
        "trade_id": row.id, "signal_id": row.signal_id, "watch_id": row.watch_id,
        "stock_code": row.stock_code, "stock_name": row.stock_name,
        "first_buy_price": row.first_buy_price, "total_buy_amount": row.total_buy_amount,
        "remaining_amount": row.remaining_amount, "stop_loss_price": row.stop_loss_price,
        "target_price": row.target_price, "trade_status": row.trade_status,
        "pnl_amount": row.pnl_amount, "holding_days": row.holding_days,
    }


# ── Watch Pool ──

@router.get("/watch-pool")
def admin_list_watch(db: Session = Depends(get_db), admin=Depends(require_admin)):
    rows = db.query(WatchPool).order_by(WatchPool.id.desc()).limit(200).all()
    return ok([_watch_row(r) for r in rows])


@router.post("/watch-pool")
def admin_add_watch(payload: dict, db: Session = Depends(get_db), admin=Depends(require_admin)):
    from app.services.prd_v1 import PrdWatchPoolService
    from app.services.normalization import normalize_stock_code
    code = normalize_stock_code(payload["stock_code"])
    existing = db.query(WatchPool).filter(WatchPool.stock_code == code, WatchPool.active.is_(True)).first()
    if existing:
        raise HTTPException(status_code=409, detail="该股票已在观察池中")
    svc = PrdWatchPoolService(db)
    row = svc.add_watch({
        "stock_code": code,
        "stock_name": payload["stock_name"],
        "trading_system": payload.get("trading_system", "uptrend"),
        "entry_reason": payload.get("entry_reason", "后台手动添加"),
        "reason": payload.get("entry_reason", "后台手动添加"),
        "key_observe_price": payload.get("key_observe_price"),
        "auto_remove_price": payload.get("auto_remove_price"),
        "invalid_condition": payload.get("invalid_condition", ""),
        "labels": payload.get("labels", ["manual"]),
    })
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
    trigger_signature = payload.get("trigger_signature") or f"admin:{watch_id}:{payload.get('strategy_name', 'manual')}:{now.isoformat()}"

    signal = WatchSignal(
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        signal_type=payload.get("signal_type", "buy"),
        buy_point_type=payload.get("buy_point_type", ""),
        strategy_name=payload.get("strategy_name", "manual_admin_signal"),
        signal_level=payload.get("signal_level", "A"),
        trading_system=watch.trading_system,
        trigger_time=now,
        trigger_date=now.date(),
        trigger_price=payload.get("trigger_price"),
        trigger_reason=payload.get("trigger_reason", "后台手动添加信号"),
        risk_desc=payload.get("risk_desc", "仅作为交易辅助"),
        stop_loss_price=payload.get("stop_loss_price"),
        target_price=payload.get("target_price"),
        buy_point_confirmed=buy_confirmed,
        buy_point_confirm_time=now if buy_confirmed else None,
        buy_point_confirm_price=(payload.get("trigger_price") if buy_confirmed else None),
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
    signal = db.query(WatchSignal).filter(WatchSignal.signal_id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="signal not found")

    existing = db.query(WatchTrade).filter(WatchTrade.signal_id == signal_id).first()
    if existing:
        return ok(_trade_row(existing), message="signal already has a trade")

    now = datetime.utcnow()
    buy_price = float(payload["buy_price"])
    amount = float(payload.get("amount", 0))

    trade = WatchTrade(
        signal_id=signal.signal_id,
        watch_id=signal.watch_id,
        stock_code=signal.stock_code,
        stock_name=signal.stock_name,
        trading_system=signal.trading_system,
        buy_point_type=signal.buy_point_type,
        first_buy_time=now,
        first_buy_price=buy_price,
        total_buy_amount=amount,
        average_buy_price=buy_price,
        remaining_amount=amount,
        position_ratio=payload.get("position_ratio"),
        stop_loss_price=payload.get("stop_loss_price"),
        target_price=payload.get("target_price"),
        buy_reason=payload.get("buy_reason", "后台手动确认交易"),
        trade_plan=payload.get("trade_plan", ""),
        trade_status="open",
    )
    db.add(trade)
    db.flush()

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

    watch = db.query(WatchPool).filter(WatchPool.id == signal.watch_id).first()
    if watch:
        watch.status = "trading"
        watch.monitor_enabled = False
        watch.signal_enabled = False

    db.commit()
    db.refresh(trade)
    return ok(_trade_row(trade))
