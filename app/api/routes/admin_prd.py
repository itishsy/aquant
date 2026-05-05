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
)
from app.services.prd_v1 import SeedService, record_operation

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
    task.running = True
    log = ConfigTaskLog(task_id=task.task_id, task_name=task.task_name, run_status="running", started_at=datetime.utcnow())
    db.add(log)
    db.commit()
    task.running = False
    log.run_status = "success"
    log.finished_at = datetime.utcnow()
    log.affected_rows = 0
    db.commit()
    return ok({"task_name": task.task_name, "run_status": log.run_status, "affected_rows": 0})


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
