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
        run_daily_market_job,
        trigger="cron",
        hour=settings.daily_collection_hour,
        minute=settings.daily_collection_minute,
        id="collect_market_daily",
        name="Collect market daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )
    return scheduler


def run_daily_market_job(trade_date: date | None = None) -> None:
    db: Session = SystemSessionLocal()
    try:
        TaskService(db).collect_market_daily(trade_date or date.today())
    finally:
        db.close()
