from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models import SystemTaskLog
from app.services.tasks import TaskService

router = APIRouter(prefix="/admin/tasks", tags=["admin"])


def ensure_admin(x_admin_token: str | None = Header(default=None)):
    if x_admin_token != get_settings().admin_token:
        raise HTTPException(status_code=401, detail="admin token required")


def china_today() -> date:
    return datetime.now(ZoneInfo(get_settings().timezone)).date()


@router.get("/logs", dependencies=[Depends(ensure_admin)])
def task_logs(db: Session = Depends(get_db)):
    return db.query(SystemTaskLog).order_by(SystemTaskLog.started_at.desc()).all()


@router.post("/{task_name}/run", dependencies=[Depends(ensure_admin)])
def run_task(
    task_name: str,
    trade_date: date | None = None,
    provider_mode: str | None = None,
    db: Session = Depends(get_db),
):
    service = TaskService(db)
    today = china_today()
    target_date = trade_date or today
    if target_date > today:
        raise HTTPException(status_code=400, detail=f"future trade_date is not allowed: {target_date}")
    mapping = {
        "collect_market_daily_task": lambda: service.collect_market_daily_task(target_date, provider_mode),
        "collect_sector_daily_task": lambda: service.collect_sector_daily_task(target_date, provider_mode),
        "collect_hot_stock_rank_task": lambda: service.collect_hot_stock_rank_task(target_date, provider_mode),
        "collect_limit_up_daily_task": lambda: service.collect_limit_up_daily_task(target_date, provider_mode),
        "auto_update_watch_pool_task": lambda: service.auto_update_watch_pool_task(target_date),
        "scan_signals_task": lambda: service.scan_signals_task(target_date),
        "generate_daily_snapshot_task": lambda: service.generate_daily_snapshot_task(target_date, provider_mode),
        "generate_weekly_review_task": lambda: service.generate_weekly_review_task(target_date),
    }
    if task_name not in mapping:
        raise HTTPException(status_code=404, detail="task not found")
    log = mapping[task_name]()
    removed_future_rows = 0
    if task_name == "generate_daily_snapshot_task":
        removed_future_rows = service.remove_future_snapshot_data(today)
    return {
        "task_name": log.task_name,
        "status": log.status,
        "affected_rows": log.affected_rows,
        "removed_future_rows": removed_future_rows,
        "provider_mode": provider_mode or get_settings().data_provider_mode,
        "trade_date": target_date,
    }
