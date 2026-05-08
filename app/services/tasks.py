from __future__ import annotations

import json
from datetime import date, datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.models import ConfigTaskLog, MktDaily, MktHotBoard, MktHotStock, MktLimitUp
from app.providers.factory import ProviderFactory


def _serialize(data: dict) -> dict:
    return json.loads(json.dumps(data, default=str))


class TaskService:
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
        except Exception as exc:
            log.run_status = "failed"
            log.error_message = str(exc)
        finally:
            log.finished_at = datetime.utcnow()
            self.db.commit()
        return log

    def collect_market_daily(self, trade_date: date) -> ConfigTaskLog:
        def _do() -> int:
            provider = ProviderFactory.create()
            snapshot = provider.get_market_snapshot(trade_date)
            existing = (
                self.db.query(MktDaily)
                .filter(MktDaily.trade_date == trade_date, MktDaily.source == "real")
                .first()
            )
            if existing:
                for k, v in snapshot.items():
                    if hasattr(existing, k):
                        setattr(existing, k, v)
                existing.source_update_time = datetime.utcnow()
                return 1
            row = MktDaily(
                trade_date=snapshot["trade_date"],
                source="real",
                sh_index=snapshot.get("sh_index"),
                sz_index=snapshot.get("sz_index"),
                cyb_index=snapshot.get("cyb_index"),
                total_amount=snapshot.get("total_amount"),
                up_count=snapshot.get("up_count"),
                down_count=snapshot.get("down_count"),
                flat_count=snapshot.get("flat_count"),
                limit_up_count=snapshot.get("limit_up_count"),
                limit_down_count=snapshot.get("limit_down_count"),
                broken_limit_count=snapshot.get("broken_limit_count"),
                max_continue_board=snapshot.get("max_continue_board"),
                source_update_time=datetime.utcnow(),
                raw_snapshot=_serialize(snapshot),
            )
            self.db.add(row)
            self.db.commit()
            return 1

        return self._run("collect_market_daily", _do)

    def collect_hot_sector_rank(self, trade_date: date) -> ConfigTaskLog:
        def _do() -> int:
            provider = ProviderFactory.create()
            sectors = provider.get_sector_daily(trade_date)
            count = 0
            for item in sectors:
                existing = (
                    self.db.query(MktHotBoard)
                    .filter(
                        MktHotBoard.trade_date == trade_date,
                        MktHotBoard.platform == "cls",
                        MktHotBoard.board_name == item["sector_name"],
                    )
                    .first()
                )
                if existing:
                    existing.change_pct = item.get("change_pct")
                    existing.leader_stock_code = item.get("leader_stock_code")
                    existing.leader_stock_name = item.get("leader_stock_name")
                    existing.source_update_time = datetime.utcnow()
                else:
                    self.db.add(
                        MktHotBoard(
                            trade_date=trade_date,
                            platform="cls",
                            board_name=item["sector_name"],
                            platform_rank=count + 1,
                            change_pct=item.get("change_pct"),
                            leader_stock_code=item.get("leader_stock_code"),
                            leader_stock_name=item.get("leader_stock_name"),
                            raw_score=item.get("fund_strength"),
                            source_update_time=datetime.utcnow(),
                            raw_payload=_serialize(item),
                        )
                    )
                count += 1
            self.db.commit()
            return count

        return self._run("collect_hot_sector_rank", _do)

    def collect_hot_stock_rank(self, trade_date: date) -> ConfigTaskLog:
        def _do() -> int:
            provider = ProviderFactory.create()
            stocks = provider.get_hot_stock_rank(trade_date)
            count = 0
            for item in stocks:
                existing = (
                    self.db.query(MktHotStock)
                    .filter(
                        MktHotStock.trade_date == trade_date,
                        MktHotStock.platform == item["platform"],
                        MktHotStock.stock_code == item["stock_code"],
                    )
                    .first()
                )
                if existing:
                    existing.platform_rank = item["platform_rank"]
                    existing.raw_score = item.get("rank_score")
                    existing.source_update_time = datetime.utcnow()
                else:
                    self.db.add(
                        MktHotStock(
                            trade_date=trade_date,
                            platform=item["platform"],
                            stock_code=item["stock_code"],
                            stock_name=item["stock_name"],
                            board_name=item.get("sector_name"),
                            platform_rank=item["platform_rank"],
                            raw_score=item.get("rank_score"),
                            raw_payload=item.get("raw_payload", {}),
                            source_update_time=datetime.utcnow(),
                        )
                    )
                count += 1
            self.db.commit()
            return count

        return self._run("collect_hot_stock_rank", _do)

    def collect_limit_up_daily(self, trade_date: date) -> ConfigTaskLog:
        def _do() -> int:
            provider = ProviderFactory.create()
            items = provider.get_limit_up_list(trade_date)
            count = 0
            for item in items:
                existing = (
                    self.db.query(MktLimitUp)
                    .filter(
                        MktLimitUp.trade_date == trade_date,
                        MktLimitUp.platform == "cls",
                        MktLimitUp.stock_code == item["stock_code"],
                    )
                    .first()
                )
                if existing:
                    existing.limit_time = item.get("limit_time")
                    existing.open_limit_count = item.get("open_limit_count")
                    existing.seal_amount = item.get("seal_amount")
                    existing.seal_volume = item.get("seal_volume")
                    existing.turnover_rate = item.get("turnover_rate")
                    existing.amount = item.get("amount")
                    existing.board_count = item.get("board_count")
                    existing.concept = item.get("concept", "")
                    existing.limit_reason = item.get("reason", "")
                    existing.source_update_time = datetime.utcnow()
                else:
                    self.db.add(
                        MktLimitUp(
                            trade_date=trade_date,
                            platform="cls",
                            stock_code=item["stock_code"],
                            stock_name=item["stock_name"],
                            limit_time=item.get("limit_time"),
                            open_limit_count=item.get("open_limit_count"),
                            seal_amount=item.get("seal_amount"),
                            seal_volume=item.get("seal_volume"),
                            turnover_rate=item.get("turnover_rate"),
                            amount=item.get("amount"),
                            board_count=item.get("board_count", 1),
                            concept=item.get("concept", ""),
                            limit_reason=item.get("reason", ""),
                            source_update_time=datetime.utcnow(),
                            raw_payload=_serialize(item),
                        )
                    )
                count += 1
            self.db.commit()
            return count

        return self._run("collect_limit_up_daily", _do)

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
