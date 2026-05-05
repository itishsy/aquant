from __future__ import annotations

from datetime import date, datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.models import ConfigTaskLog


class TaskService:
    """PRD v1 task runner.

    Tasks log to config_task_log and do not perform auto watch-pool insertion or
    any trading action.
    """

    def __init__(self, db: Session):
        self.db = db

    def _run(self, task_name: str, fn: Callable[[], int]) -> ConfigTaskLog:
        log = ConfigTaskLog(task_name=task_name, run_status="running", started_at=datetime.utcnow())
        self.db.add(log)
        self.db.commit()
        try:
            affected = fn()
            log.run_status = "success"
            log.affected_rows = affected
        except Exception as exc:  # pragma: no cover - defensive task logging
            log.run_status = "failed"
            log.error_message = str(exc)
        finally:
            log.finished_at = datetime.utcnow()
            self.db.commit()
        return log

    def collect_market_daily(self, trade_date: date) -> ConfigTaskLog:
        return self._run("collect_market_daily", lambda: 0)

    def collect_hot_sector_rank(self, trade_date: date) -> ConfigTaskLog:
        return self._run("collect_hot_sector_rank", lambda: 0)

    def collect_hot_stock_rank(self, trade_date: date) -> ConfigTaskLog:
        return self._run("collect_hot_stock_rank", lambda: 0)

    def collect_limit_up_daily(self, trade_date: date) -> ConfigTaskLog:
        return self._run("collect_limit_up_daily", lambda: 0)

    def update_watch_daily_kline(self, trade_date: date) -> ConfigTaskLog:
        return self._run("update_watch_daily_kline", lambda: 0)

    def update_watch_15m_kline(self, trade_date: date) -> ConfigTaskLog:
        return self._run("update_watch_15m_kline", lambda: 0)

    def scan_watch_signals(self, trade_date: date) -> ConfigTaskLog:
        return self._run("scan_watch_signals", lambda: 0)

    def scan_trade_risk_signals(self, trade_date: date) -> ConfigTaskLog:
        return self._run("scan_trade_risk_signals", lambda: 0)

    def generate_weekly_review_form(self, trade_date: date) -> ConfigTaskLog:
        return self._run("generate_weekly_review_form", lambda: 0)

    def generate_monthly_review_form(self, trade_date: date) -> ConfigTaskLog:
        return self._run("generate_monthly_review_form", lambda: 0)

    def remind_pending_review_form(self, trade_date: date) -> ConfigTaskLog:
        return self._run("remind_pending_review_form", lambda: 0)

    def aggregate_review_metrics(self, trade_date: date) -> ConfigTaskLog:
        return self._run("aggregate_review_metrics", lambda: 0)
