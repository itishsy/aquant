from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import SystemTaskLog
from app.services.hot_stock import HotStockService
from app.services.limit_up import LimitUpService
from app.services.market import MarketService
from app.services.review import ReviewService
from app.services.sector import SectorService
from app.services.signal_engine import SignalEngine
from app.services.watch_pool import WatchPoolService


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def _run(self, task_name: str, func):
        started = datetime.utcnow()
        log = SystemTaskLog(task_name=task_name, status="running", started_at=started, affected_rows=0)
        self.db.add(log)
        self.db.commit()
        try:
            affected_rows = func()
            log.status = "success"
            log.affected_rows = affected_rows if isinstance(affected_rows, int) else len(affected_rows or [])
            log.finished_at = datetime.utcnow()
            self.db.commit()
            return log
        except Exception as exc:
            log.status = "failed"
            log.error_message = str(exc)
            log.finished_at = datetime.utcnow()
            self.db.commit()
            raise

    def collect_market_daily_task(self, trade_date: date):
        return self._run("collect_market_daily_task", lambda: 1 if MarketService(self.db).collect_market_daily(trade_date) else 0)

    def collect_sector_daily_task(self, trade_date: date):
        return self._run("collect_sector_daily_task", lambda: SectorService(self.db).collect_sector_daily(trade_date))

    def collect_hot_stock_rank_task(self, trade_date: date):
        return self._run("collect_hot_stock_rank_task", lambda: HotStockService(self.db).collect_hot_stock_rank(trade_date))

    def collect_limit_up_daily_task(self, trade_date: date):
        return self._run("collect_limit_up_daily_task", lambda: LimitUpService(self.db).collect_limit_up_daily(trade_date))

    def auto_update_watch_pool_task(self, trade_date: date):
        return self._run("auto_update_watch_pool_task", lambda: WatchPoolService(self.db).auto_add_candidates(trade_date))

    def scan_signals_task(self, trade_date: date):
        return self._run("scan_signals_task", lambda: SignalEngine(self.db).scan())

    def generate_daily_snapshot_task(self, trade_date: date):
        return self._run(
            "generate_daily_snapshot_task",
            lambda: [
                MarketService(self.db).collect_market_daily(trade_date),
                *SectorService(self.db).collect_sector_daily(trade_date),
            ],
        )

    def generate_weekly_review_task(self, trade_date: date):
        week_start = trade_date - timedelta(days=trade_date.weekday())
        return self._run(
            "generate_weekly_review_task",
            lambda: ReviewService(self.db).generate_weekly_review(week_start, trade_date),
        )
