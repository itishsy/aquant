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
    scheduler.add_job(
        run_watch_price_update,
        trigger="interval",
        minutes=5,
        id="update_watch_prices",
        name="Update watch stock prices",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        run_watch_signal_scan,
        trigger="interval",
        minutes=15,
        id="scan_watch_signals",
        name="Scan watch-pool signals",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        run_watch_rule_scan,
        trigger="interval",
        minutes=10,
        id="scan_watch_rules",
        name="Scan watch-pool trading system rules",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        run_trade_rule_scan,
        trigger="interval",
        minutes=10,
        id="scan_trade_rules",
        name="Scan active trade trading system rules",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        run_watch_auto_remove,
        trigger="interval",
        minutes=15,
        id="auto_remove_watch_pool",
        name="Auto remove watch-pool items",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
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


def run_watch_signal_scan() -> None:
    db: Session = SystemSessionLocal()
    try:
        TaskService(db).scan_watch_signals(date.today())
    finally:
        db.close()


def run_watch_rule_scan() -> None:
    db: Session = SystemSessionLocal()
    try:
        TaskService(db).scan_watch_rules(date.today())
    finally:
        db.close()


def run_trade_rule_scan() -> None:
    db: Session = SystemSessionLocal()
    try:
        TaskService(db).scan_trade_rules(date.today())
    finally:
        db.close()


def run_watch_price_update() -> None:
    db: Session = SystemSessionLocal()
    try:
        TaskService(db).update_watch_prices(date.today())
    finally:
        db.close()


def run_watch_auto_remove() -> None:
    db: Session = SystemSessionLocal()
    try:
        TaskService(db).auto_remove_watch_pool(date.today())
    finally:
        db.close()
