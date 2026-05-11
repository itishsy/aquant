from __future__ import annotations

import json
from datetime import date, datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.models import (
    ConfigTaskLog,
    MktDaily,
    MktDailyChance,
    MktDailyChanceStock,
    MktDailyTopic,
    MktDailyTopicStock,
    MktDailyTuyere,
    MktDailyTuyereStock,
    MktHotBoard,
    MktHotStock,
    MktLimitUp,
    MktLimitUpLadder,
    MktLimitUpLadderStock,
    MktLimitUpPlate,
    MktLimitUpStock,
)
from app.providers.factory import ProviderFactory


def _serialize(data: dict) -> dict:
    return json.loads(json.dumps(data, default=str))


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def _replace_market_structured_rows(self, trade_date: date, snapshot: dict) -> int:
        existing_chance_ids = [
            row.id for row in self.db.query(MktDailyChance.id).filter(MktDailyChance.trade_date == trade_date).all()
        ]
        existing_tuyere_ids = [
            row.id for row in self.db.query(MktDailyTuyere.id).filter(MktDailyTuyere.trade_date == trade_date).all()
        ]
        existing_topic_ids = [
            row.id for row in self.db.query(MktDailyTopic.id).filter(MktDailyTopic.trade_date == trade_date).all()
        ]
        existing_ladder_ids = [
            row.id for row in self.db.query(MktLimitUpLadder.id).filter(MktLimitUpLadder.trade_date == trade_date).all()
        ]

        if existing_chance_ids:
            self.db.query(MktDailyChanceStock).filter(MktDailyChanceStock.chance_id.in_(existing_chance_ids)).delete(synchronize_session=False)
        if existing_tuyere_ids:
            self.db.query(MktDailyTuyereStock).filter(MktDailyTuyereStock.tuyere_id.in_(existing_tuyere_ids)).delete(synchronize_session=False)
        if existing_topic_ids:
            self.db.query(MktDailyTopicStock).filter(MktDailyTopicStock.topic_id.in_(existing_topic_ids)).delete(synchronize_session=False)
        if existing_ladder_ids:
            self.db.query(MktLimitUpLadderStock).filter(MktLimitUpLadderStock.ladder_id.in_(existing_ladder_ids)).delete(synchronize_session=False)

        self.db.query(MktDailyChance).filter(MktDailyChance.trade_date == trade_date).delete(synchronize_session=False)
        self.db.query(MktDailyTuyere).filter(MktDailyTuyere.trade_date == trade_date).delete(synchronize_session=False)
        self.db.query(MktDailyTopic).filter(MktDailyTopic.trade_date == trade_date).delete(synchronize_session=False)
        self.db.query(MktLimitUpLadder).filter(MktLimitUpLadder.trade_date == trade_date).delete(synchronize_session=False)
        self.db.flush()

        affected = 0
        now = datetime.utcnow()
        for rank_no, item in enumerate(snapshot.get("today_chances") or [], start=1):
            row = MktDailyChance(
                trade_date=trade_date,
                source="real",
                platform=item.get("source") or "cls",
                rank_no=rank_no,
                subject_id=item.get("subject_id"),
                subject_name=item.get("subject_name") or "",
                article_id=item.get("article_id"),
                article_title=item.get("title") or "",
                article_time=item.get("article_time"),
                attention_num=item.get("attention_num"),
                source_update_time=now,
            )
            self.db.add(row)
            self.db.flush()
            for stock in item.get("stocks") or []:
                self.db.add(MktDailyChanceStock(
                    chance_id=row.id,
                    stock_code=stock.get("stock_code") or "",
                    stock_name=stock.get("stock_name") or "",
                    change_pct=stock.get("change_pct"),
                    last_price=stock.get("last_price"),
                ))
            affected += 1

        for rank_no, item in enumerate(snapshot.get("today_tuyeres") or [], start=1):
            row = MktDailyTuyere(
                trade_date=trade_date,
                source="real",
                platform=item.get("source") or "cls",
                rank_no=rank_no,
                subject_id=item.get("subject_id"),
                subject_name=item.get("subject_name") or "",
                driver=item.get("driver") or item.get("title") or "",
                attention_num=item.get("attention_num"),
                source_update_time=now,
            )
            self.db.add(row)
            self.db.flush()
            for stock in item.get("stocks") or []:
                self.db.add(MktDailyTuyereStock(
                    tuyere_id=row.id,
                    stock_code=stock.get("stock_code") or "",
                    stock_name=stock.get("stock_name") or "",
                    change_pct=stock.get("change_pct"),
                    last_price=stock.get("last_price"),
                ))
            affected += 1

        for item in snapshot.get("topic_list") or []:
            row = MktDailyTopic(
                trade_date=trade_date,
                source="real",
                platform=item.get("source") or "ths",
                rank_no=item.get("rank_no"),
                topic_code=item.get("topic_code") or "",
                title=item.get("title") or "",
                description=item.get("description") or "",
                subtitle=item.get("subtitle") or "",
                hot_value=item.get("hot_value"),
                jump_url=item.get("jump_url"),
                source_update_time=now,
            )
            self.db.add(row)
            self.db.flush()
            for stock in item.get("stocks") or []:
                self.db.add(MktDailyTopicStock(
                    topic_id=row.id,
                    stock_code=stock.get("stock_code") or "",
                    stock_name=stock.get("stock_name") or "",
                    change_pct=stock.get("change_pct"),
                ))
            affected += 1

        for item in snapshot.get("limit_up_ladder") or []:
            row = MktLimitUpLadder(
                trade_date=trade_date,
                source="real",
                platform="cls",
                height=item.get("height") or 0,
                stock_count=item.get("count") or 0,
                source_update_time=now,
            )
            self.db.add(row)
            self.db.flush()
            for stock in item.get("stocks") or []:
                self.db.add(MktLimitUpLadderStock(
                    ladder_id=row.id,
                    stock_code=stock.get("stock_code") or "",
                    stock_name=stock.get("stock_name") or "",
                ))
            affected += 1

        return affected

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
                    if hasattr(existing, k) and k not in {"today_chances", "today_tuyeres", "topic_list", "limit_up_ladder"}:
                        setattr(existing, k, v)
                existing.source_update_time = datetime.utcnow()
                return 1 + self._replace_market_structured_rows(trade_date, snapshot)
            row = MktDaily(
                trade_date=snapshot["trade_date"],
                source="real",
                sh_index=snapshot.get("sh_index"),
                sz_index=snapshot.get("sz_index"),
                cyb_index=snapshot.get("cyb_index"),
                index_change_pct=snapshot.get("index_change_pct"),
                sh_index_change_pct=snapshot.get("sh_index_change_pct"),
                sh_index_change_px=snapshot.get("sh_index_change_px"),
                sz_index_change_pct=snapshot.get("sz_index_change_pct"),
                sz_index_change_px=snapshot.get("sz_index_change_px"),
                cyb_index_change_pct=snapshot.get("cyb_index_change_pct"),
                cyb_index_change_px=snapshot.get("cyb_index_change_px"),
                index_trade_status=snapshot.get("index_trade_status") or {},
                total_amount=snapshot.get("total_amount"),
                up_count=snapshot.get("up_count"),
                down_count=snapshot.get("down_count"),
                flat_count=snapshot.get("flat_count"),
                limit_up_count=snapshot.get("limit_up_count"),
                limit_down_count=snapshot.get("limit_down_count"),
                broken_limit_count=snapshot.get("broken_limit_count"),
                max_continue_board=snapshot.get("max_continue_board"),
                source_url=snapshot.get("source_url"),
                source_update_time=datetime.utcnow(),
                raw_snapshot=_serialize(snapshot.get("raw_snapshot") or snapshot),
            )
            self.db.add(row)
            self.db.commit()
            return 1 + self._replace_market_structured_rows(trade_date, snapshot)

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
                    existing.price = item.get("price")
                    existing.change_pct = item.get("change_pct")
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
                            price=item.get("price"),
                            change_pct=item.get("change_pct"),
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
            if hasattr(provider, "get_limit_up_analysis"):
                analysis = provider.get_limit_up_analysis(trade_date)
                self.db.query(MktLimitUpStock).filter(MktLimitUpStock.trade_date == trade_date).delete(synchronize_session=False)
                self.db.query(MktLimitUpPlate).filter(MktLimitUpPlate.trade_date == trade_date).delete(synchronize_session=False)
                self.db.query(MktLimitUpLadder).filter(MktLimitUpLadder.trade_date == trade_date).delete(synchronize_session=False)
                self.db.flush()

                now = datetime.utcnow()
                count = 0
                for item in analysis.get("plates") or []:
                    self.db.add(MktLimitUpPlate(
                        trade_date=trade_date,
                        source=item.get("source") or "real",
                        platform=item.get("platform") or "cls",
                        plate_code=item.get("plate_code") or "",
                        plate_name=item.get("plate_name") or "",
                        change_pct=item.get("change_pct"),
                        limit_up_count=item.get("limit_up_count"),
                        up_reason=item.get("up_reason") or "",
                        source_update_time=now,
                    ))
                    count += 1
                for item in analysis.get("ladders") or []:
                    self.db.add(MktLimitUpLadder(
                        trade_date=trade_date,
                        source="real",
                        platform="cls",
                        height=item.get("height") or 0,
                        stock_count=item.get("count") or 0,
                        source_update_time=now,
                    ))
                    count += 1
                for item in analysis.get("stocks") or []:
                    self.db.add(MktLimitUpStock(
                        trade_date=trade_date,
                        source=item.get("source") or "real",
                        platform=item.get("platform") or "cls",
                        stock_code=item.get("stock_code") or "",
                        stock_name=item.get("stock_name") or "",
                        plate_code=item.get("plate_code") or "",
                        plate_name=item.get("plate_name") or "",
                        change_pct=item.get("change_pct"),
                        last_price=item.get("last_price"),
                        circulating_market_cap=item.get("circulating_market_cap"),
                        limit_time=item.get("limit_time"),
                        board_count=item.get("board_count"),
                        board_text=item.get("board_text") or "",
                        limit_reason=item.get("limit_reason") or "",
                        reason_tags=item.get("reason_tags") or "",
                        ladder_height=item.get("ladder_height"),
                        source_update_time=now,
                    ))
                    count += 1
                self.db.commit()
                return count

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
