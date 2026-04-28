from datetime import date

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


@router.get("/logs", dependencies=[Depends(ensure_admin)])
def task_logs(db: Session = Depends(get_db)):
    return db.query(SystemTaskLog).order_by(SystemTaskLog.started_at.desc()).all()


@router.post("/{task_name}/run", dependencies=[Depends(ensure_admin)])
def run_task(task_name: str, db: Session = Depends(get_db)):
    service = TaskService(db)
    today = date.today()
    mapping = {
        "collect_market_daily_task": lambda: service.collect_market_daily_task(today),
        "collect_sector_daily_task": lambda: service.collect_sector_daily_task(today),
        "collect_hot_stock_rank_task": lambda: service.collect_hot_stock_rank_task(today),
        "collect_limit_up_daily_task": lambda: service.collect_limit_up_daily_task(today),
        "auto_update_watch_pool_task": lambda: service.auto_update_watch_pool_task(today),
        "scan_signals_task": lambda: service.scan_signals_task(today),
        "generate_daily_snapshot_task": lambda: service.generate_daily_snapshot_task(today),
        "generate_weekly_review_task": lambda: service.generate_weekly_review_task(today),
    }
    if task_name not in mapping:
        raise HTTPException(status_code=404, detail="task not found")
    log = mapping[task_name]()
    return {"task_name": log.task_name, "status": log.status, "affected_rows": log.affected_rows}
