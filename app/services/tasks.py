from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import HotStockRank, LimitUpDaily, MarketDaily, MarketReviewDaily, SectorDaily, SystemTaskLog
from app.providers.factory import ProviderFactory
from app.services.hot_stock import HotStockService
from app.services.limit_up import LimitUpService
from app.services.market import MarketService
from app.services.market_review import MarketReviewService
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

    def collect_market_daily_task(self, trade_date: date, provider_mode: str | None = None):
        return self._run("collect_market_daily_task", lambda: self._with_provider(provider_mode, lambda: 1 if MarketService(self.db).collect_market_daily(trade_date) else 0))

    def collect_sector_daily_task(self, trade_date: date, provider_mode: str | None = None):
        return self._run("collect_sector_daily_task", lambda: self._with_provider(provider_mode, lambda: SectorService(self.db).collect_sector_daily(trade_date)))

    def collect_hot_stock_rank_task(self, trade_date: date, provider_mode: str | None = None):
        return self._run("collect_hot_stock_rank_task", lambda: self._with_provider(provider_mode, lambda: HotStockService(self.db).collect_hot_stock_rank(trade_date)))

    def collect_limit_up_daily_task(self, trade_date: date, provider_mode: str | None = None):
        return self._run("collect_limit_up_daily_task", lambda: self._with_provider(provider_mode, lambda: LimitUpService(self.db).collect_limit_up_daily(trade_date)))

    def auto_update_watch_pool_task(self, trade_date: date):
        return self._run("auto_update_watch_pool_task_deprecated_noop", lambda: [])

    def scan_signals_task(self, trade_date: date):
        return self._run("scan_signals_task", lambda: SignalEngine(self.db).scan())

    def generate_daily_snapshot_task(self, trade_date: date, provider_mode: str | None = None):
        return self._run(
            "generate_daily_snapshot_task",
            lambda: self._with_provider(provider_mode, lambda: self._collect_daily_snapshot(trade_date)),
        )

    @staticmethod
    def _with_provider(provider_mode: str | None, func):
        with ProviderFactory.use_mode(provider_mode):
            return func()

    def _collect_daily_snapshot(self, trade_date: date) -> int:
        affected_rows = 0
        errors: list[str] = []
        steps = [
            ("market", lambda: [MarketService(self.db).collect_market_daily(trade_date)]),
            ("sector", lambda: SectorService(self.db).collect_sector_daily(trade_date)),
            ("hot_stock", lambda: HotStockService(self.db).collect_hot_stock_rank(trade_date)),
            ("limit_up", lambda: LimitUpService(self.db).collect_limit_up_daily(trade_date)),
            ("market_review", lambda: [MarketReviewService(self.db).collect_market_review(trade_date)]),
        ]
        for step_name, step in steps:
            try:
                result = step()
                affected_rows += len(result or [])
            except Exception as exc:
                errors.append(f"{step_name}: {exc}")
                self.db.rollback()
        if affected_rows == 0 and errors:
            raise RuntimeError("; ".join(errors))
        return affected_rows

    def remove_future_snapshot_data(self, cutoff_date: date) -> int:
        models = [MarketDaily, SectorDaily, HotStockRank, LimitUpDaily, MarketReviewDaily]
        removed = 0
        for model in models:
            removed += self.db.query(model).filter(model.trade_date > cutoff_date).delete(synchronize_session=False)
        self.db.commit()
        return removed

    def generate_weekly_review_task(self, trade_date: date):
        week_start = trade_date - timedelta(days=trade_date.weekday())
        return self._run(
            "generate_weekly_review_task",
            lambda: ReviewService(self.db).generate_weekly_review(week_start, trade_date),
        )
