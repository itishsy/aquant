from __future__ import annotations

from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SystemSessionLocal
from app.services.tasks import TaskService


def build_scheduler() -> BackgroundScheduler:
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=settings.timezone)
    scheduler.add_job(
        run_daily_collect_all,
        trigger="cron",
        hour=18,
        minute=0,
        id="collect_all_market",
        name="Collect all market data daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )
    return scheduler


def run_daily_collect_all() -> None:
    db: Session = SystemSessionLocal()
    try:
        svc = TaskService(db)
        today = date.today()
        for fn in [svc.collect_market_daily, svc.collect_hot_sector_rank, svc.collect_hot_stock_rank, svc.collect_limit_up_daily]:
            fn(today)
    finally:
        db.close()
