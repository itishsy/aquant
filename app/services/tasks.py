from __future__ import annotations

import json
from datetime import date, datetime, time
from types import SimpleNamespace
from typing import Callable

from sqlalchemy.orm import Session

from app.models import (
    ConfigTask,
    ConfigTaskLog,
    MktDaily,
    MktDailyPlate,
    MktDailyPlateStock,
    MktDailyTopic,
    MktDailyTopicStock,
    MktHotStock,
    MktLimitUpStock,
    MktStockQuote,
    TradingRuleDefinition,
    TradingSystemRuleBinding,
    WatchPool,
    WatchSignal,
    WatchTrade,
)
from app.providers.factory import ProviderFactory


def _serialize(data: dict) -> dict:
    return json.loads(json.dumps(data, default=str))


class TaskService:
    SAFE_RULE_EXECUTORS = {
        "always_false",
        "not_break_price",
        "macd_bottom_divergence",
        "macd_top_divergence",
        "macd_dead_cross",
        "break_price",
    }

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _is_ignored_limit_up_plate(plate_name: str | None) -> bool:
        return (plate_name or "").strip() in {"ST\u80a1", "\u5176\u4ed6", "\u5176\u5b83"}

    @staticmethod
    def _append_text(existing: str | None, value: str | None) -> str:
        parts = [part.strip() for part in (existing or "").split("；") if part.strip()]
        for part in [p.strip() for p in (value or "").replace(",", "；").split("；") if p.strip()]:
            if part not in parts:
                parts.append(part)
        return "；".join(parts)

    @staticmethod
    def _hot_stock_code(stock_code: str | None) -> str:
        text = str(stock_code or "").strip()
        lower = text.lower()
        if lower.startswith(("sh", "sz", "bj")):
            return lower
        if "." in text:
            code, market = text.split(".", 1)
            return f"{market.lower()}{code}"
        market = "sh" if text.startswith("6") else "bj" if text.startswith(("4", "8")) else "sz"
        return f"{market}{text}" if text else ""

    @staticmethod
    def _hot_score(row: MktHotStock) -> int:
        prime_scores = {1: 71, 2: 67, 3: 61, 4: 59, 5: 53, 6: 47, 7: 43, 8: 41, 9: 37, 10: 31}
        total = 0
        for rank in (row.cls_rank, row.ths_rank, row.tgb_rank):
            if rank and 1 <= rank <= 10:
                total += prime_scores.get(rank, 0)
        return total

    @staticmethod
    def _hot_score_from_ranks(cls_rank: int | None, ths_rank: int | None, tgb_rank: int | None) -> int:
        prime_scores = {1: 71, 2: 67, 3: 61, 4: 59, 5: 53, 6: 47, 7: 43, 8: 41, 9: 37, 10: 31}
        return sum(prime_scores.get(rank, 0) for rank in (cls_rank, ths_rank, tgb_rank) if rank and 1 <= rank <= 10)

    def _quote_for_hot_stock(self, provider, stock_code: str) -> dict:
        if hasattr(provider, "get_stock_quote"):
            return provider.get_stock_quote(stock_code) or {}
        return {}

    @staticmethod
    def _missing_hot_price(value) -> bool:
        try:
            return value is None or float(value) <= 0
        except (TypeError, ValueError):
            return True

    @staticmethod
    def _missing_hot_change(value) -> bool:
        return value is None

    def _matched_assoc_plates(self, trade_date: date, assoc_rows: list[dict]) -> tuple[str, str]:
        names = [str(item.get("plate_name") or "").strip() for item in assoc_rows if item.get("plate_name")]
        desc = next((str(item.get("assoc_desc") or "").strip() for item in assoc_rows if item.get("assoc_desc")), "")
        if not names:
            return "", desc
        recent = (
            self.db.query(MktDailyPlate.plate_name)
            .filter(MktDailyPlate.trade_date <= trade_date)
            .order_by(MktDailyPlate.trade_date.desc(), MktDailyPlate.id.desc())
            .limit(30)
            .all()
        )
        matched = []
        for row in recent:
            if row.plate_name in names and row.plate_name not in matched:
                matched.append(row.plate_name)
        return ",".join(matched or names[:2]), desc

    def _replace_market_structured_rows(self, trade_date: date, snapshot: dict) -> int:
        existing_plate_ids = [
            row.id
            for row in self.db.query(MktDailyPlate.id)
            .filter(MktDailyPlate.trade_date == trade_date, MktDailyPlate.plate_type.in_(["chance", "tuyere"]))
            .all()
        ]
        existing_topic_ids = [
            row.id for row in self.db.query(MktDailyTopic.id).filter(MktDailyTopic.trade_date == trade_date).all()
        ]
        if existing_plate_ids:
            self.db.query(MktDailyPlateStock).filter(MktDailyPlateStock.plate_id.in_(existing_plate_ids)).delete(synchronize_session=False)
        if existing_topic_ids:
            self.db.query(MktDailyTopicStock).filter(MktDailyTopicStock.topic_id.in_(existing_topic_ids)).delete(synchronize_session=False)

        self.db.query(MktDailyPlate).filter(MktDailyPlate.trade_date == trade_date, MktDailyPlate.plate_type.in_(["chance", "tuyere"])).delete(synchronize_session=False)
        self.db.query(MktDailyTopic).filter(MktDailyTopic.trade_date == trade_date).delete(synchronize_session=False)
        self.db.flush()

        affected = 0
        now = datetime.utcnow()
        for rank_no, item in enumerate(snapshot.get("today_chances") or [], start=1):
            subject_id = item.get("subject_id")
            plate_code = str(subject_id or "")
            plate_name = item.get("subject_name") or item.get("title") or ""
            row = MktDailyPlate(
                trade_date=trade_date,
                plate_type="chance",
                platform=item.get("source") or "cls",
                rank_no=rank_no,
                plate_code=plate_code or f"chance:{rank_no}",
                plate_name=plate_name,
                description=item.get("description") or item.get("title") or "",
                jump_url=item.get("jump_url"),
            )
            self.db.add(row)
            self.db.flush()
            for stock in item.get("stocks") or []:
                self.db.add(MktDailyPlateStock(
                    plate_id=row.id,
                    stock_code=stock.get("stock_code") or "",
                    stock_name=stock.get("stock_name") or "",
                    change_pct=stock.get("change_pct"),
                    last_price=stock.get("last_price"),
                ))
            affected += 1

        for rank_no, item in enumerate(snapshot.get("today_tuyeres") or [], start=1):
            subject_id = item.get("subject_id")
            plate_code = str(subject_id or "")
            plate_name = item.get("subject_name") or item.get("title") or ""
            driver = item.get("driver") or item.get("title") or ""
            row = MktDailyPlate(
                trade_date=trade_date,
                plate_type="tuyere",
                platform=item.get("source") or "cls",
                rank_no=rank_no,
                plate_code=plate_code or f"tuyere:{rank_no}",
                plate_name=plate_name,
                description=item.get("description") or driver,
                jump_url=item.get("jump_url"),
            )
            self.db.add(row)
            self.db.flush()
            for stock in item.get("stocks") or []:
                self.db.add(MktDailyPlateStock(
                    plate_id=row.id,
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

        return affected

    def _run(self, task_name: str, fn: Callable[[], int | tuple[int, str]]) -> ConfigTaskLog:
        task = self.db.query(ConfigTask).filter(ConfigTask.task_name == task_name).first()
        log = ConfigTaskLog(
            task_id=task.task_id if task else None,
            task_name=task_name,
            run_status="running",
            started_at=datetime.utcnow(),
        )
        if task:
            task.running = True
        self.db.add(log)
        self.db.commit()
        try:
            outcome = fn()
            if isinstance(outcome, tuple):
                affected, error_summary = outcome
            else:
                affected, error_summary = outcome, ""
            log.run_status = "success"
            log.affected_rows = affected
            if error_summary:
                log.error_message = error_summary[:2000]
        except Exception as exc:
            log.run_status = "failed"
            log.error_message = str(exc)
        finally:
            if task:
                task.running = False
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
            existing_ids = [
                row.id
                for row in self.db.query(MktDailyPlate.id)
                .filter(MktDailyPlate.trade_date == trade_date, MktDailyPlate.plate_type == "hot_board")
                .all()
            ]
            if existing_ids:
                self.db.query(MktDailyPlateStock).filter(MktDailyPlateStock.plate_id.in_(existing_ids)).delete(synchronize_session=False)
            self.db.query(MktDailyPlate).filter(MktDailyPlate.trade_date == trade_date, MktDailyPlate.plate_type == "hot_board").delete(synchronize_session=False)
            self.db.flush()

            count = 0
            for rank_no, item in enumerate(sectors, start=1):
                plate_name = item.get("sector_name") or item.get("board_name") or ""
                row = MktDailyPlate(
                    trade_date=trade_date,
                    plate_type="hot_board",
                    platform=item.get("platform") or "cls",
                    rank_no=rank_no,
                    plate_code=item.get("sector_code") or item.get("board_code") or f"hot_board:{rank_no}",
                    plate_name=plate_name,
                    description=item.get("reason") or "",
                )
                self.db.add(row)
                self.db.flush()
                if item.get("leader_stock_code"):
                    self.db.add(MktDailyPlateStock(
                        plate_id=row.id,
                        stock_code=item.get("leader_stock_code") or "",
                        stock_name=item.get("leader_stock_name") or "",
                        change_pct=item.get("change_pct"),
                    ))
                count += 1
            self.db.commit()
            return count

        return self._run("collect_hot_sector_rank", _do)

    def collect_hot_stock_rank(self, trade_date: date) -> ConfigTaskLog:
        def _do() -> int:
            provider = ProviderFactory.create()
            stocks = provider.get_hot_stock_rank(trade_date)
            merged: dict[str, dict] = {}
            for item in stocks:
                stock_code = self._hot_stock_code(item.get("stock_code"))
                if not stock_code:
                    continue
                quote = {}
                raw_price = item.get("price")
                raw_change = item.get("change_pct")
                should_quote = self._missing_hot_price(raw_price) or raw_change is None or raw_change == 0
                if should_quote:
                    quote = self._quote_for_hot_stock(provider, stock_code)
                price = quote.get("price") if self._missing_hot_price(raw_price) else raw_price
                if raw_change is None or raw_change == 0:
                    change_pct = quote.get("change_pct") if quote.get("change_pct") is not None else raw_change
                else:
                    change_pct = raw_change
                if self._missing_hot_price(price) or self._missing_hot_change(change_pct):
                    continue
                row = merged.setdefault(
                    stock_code,
                    {
                        "stock_code": stock_code,
                        "stock_name": item.get("stock_name") or "",
                        "assoc_plate": "",
                        "cls_rank": None,
                        "ths_rank": None,
                        "tgb_rank": None,
                        "price": price,
                        "change_pct": change_pct,
                        "reason": "",
                        "tag": "",
                    },
                )
                row["stock_name"] = item.get("stock_name") or row["stock_name"]
                row["price"] = row["price"] if not self._missing_hot_price(row["price"]) else price
                row["change_pct"] = row["change_pct"] if row["change_pct"] is not None else change_pct
                row[item["rank_field"]] = item["rank"]
                row["reason"] = self._append_text(row["reason"], item.get("reason"))
                row["tag"] = self._append_text(row["tag"], item.get("tag"))
                row["assoc_plate"] = self._append_text(row["assoc_plate"], item.get("assoc_plate"))

            self.db.query(MktHotStock).filter(MktHotStock.trade_date == trade_date).delete(synchronize_session=False)
            count = 0
            for data in merged.values():
                assoc_rows = provider.get_assoc_plates(data["stock_code"]) if hasattr(provider, "get_assoc_plates") else []
                assoc_plate, assoc_desc = self._matched_assoc_plates(trade_date, assoc_rows)
                data["assoc_plate"] = assoc_plate or data["assoc_plate"]
                data["reason"] = data["reason"] or assoc_desc or data["assoc_plate"]
                data["score"] = self._hot_score_from_ranks(data["cls_rank"], data["ths_rank"], data["tgb_rank"])
                self.db.add(MktHotStock(trade_date=trade_date, **data))
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
                existing_plate_ids = [
                    row.id for row in self.db.query(MktDailyPlate.id).filter(MktDailyPlate.trade_date == trade_date, MktDailyPlate.plate_type == "limit_up").all()
                ]
                if existing_plate_ids:
                    self.db.query(MktDailyPlateStock).filter(MktDailyPlateStock.plate_id.in_(existing_plate_ids)).delete(synchronize_session=False)
                self.db.query(MktDailyPlate).filter(MktDailyPlate.trade_date == trade_date, MktDailyPlate.plate_type == "limit_up").delete(synchronize_session=False)
                self.db.flush()

                now = datetime.utcnow()
                count = 0
                plate_id_by_code: dict[str, int] = {}
                eligible_plates = [
                    item for item in (analysis.get("plates") or [])
                    if not self._is_ignored_limit_up_plate(item.get("plate_name"))
                ]
                top_plates = sorted(
                    eligible_plates,
                    key=lambda row: (row.get("limit_up_count") or 0, row.get("change_pct") or 0),
                    reverse=True,
                )[:3]
                for rank_no, item in enumerate(top_plates, start=1):
                    plate_code = item.get("plate_code") or ""
                    plate_name = item.get("plate_name") or ""
                    row = MktDailyPlate(
                        trade_date=trade_date,
                        plate_type="limit_up",
                        platform=item.get("platform") or "cls",
                        rank_no=rank_no,
                        plate_code=plate_code,
                        plate_name=plate_name,
                        description=item.get("up_reason") or "",
                    )
                    self.db.add(row)
                    self.db.flush()
                    plate_id_by_code[plate_code] = row.id
                    count += 1
                for item in analysis.get("stocks") or []:
                    plate_code = item.get("plate_code") or ""
                    self.db.add(MktLimitUpStock(
                        trade_date=trade_date,
                        source=item.get("source") or "real",
                        platform=item.get("platform") or "cls",
                        raw_secu_code=item.get("raw_secu_code") or "",
                        stock_code=item.get("stock_code") or "",
                        stock_name=item.get("stock_name") or "",
                        plate_code=item.get("plate_code") or "",
                        plate_name=item.get("plate_name") or "",
                        change_pct=item.get("change_pct"),
                        last_price=item.get("last_price"),
                        circulating_market_cap=item.get("circulating_market_cap"),
                        limit_time=item.get("limit_time"),
                        limit_datetime=item.get("limit_datetime"),
                        board_days=item.get("board_days"),
                        board_count=item.get("board_count"),
                        board_text=item.get("board_text") or "",
                        limit_reason=item.get("limit_reason") or "",
                        reason_tags=item.get("reason_tags") or "",
                        ladder_height=item.get("ladder_height"),
                        source_update_time=now,
                    ))
                    plate_id = plate_id_by_code.get(plate_code)
                    if plate_id:
                        self.db.add(MktDailyPlateStock(
                            plate_id=plate_id,
                            stock_code=item.get("stock_code") or "",
                            stock_name=item.get("stock_name") or "",
                            change_pct=item.get("change_pct"),
                            last_price=item.get("last_price"),
                        ))
                    count += 1
                self.db.commit()
                return count

            items = provider.get_limit_up_list(trade_date)
            count = 0
            for item in items:
                existing = (
                    self.db.query(MktLimitUpStock)
                    .filter(
                        MktLimitUpStock.trade_date == trade_date,
                        MktLimitUpStock.source == "mock",
                        MktLimitUpStock.stock_code == item["stock_code"],
                    )
                    .first()
                ) or MktLimitUpStock(trade_date=trade_date, source="mock", platform="mock", stock_code=item["stock_code"])
                existing.stock_name = item.get("stock_name", "")
                existing.plate_name = item.get("concept", "")
                existing.limit_time = item.get("limit_time")
                existing.limit_datetime = None
                existing.board_days = None
                existing.board_count = item.get("board_count", 1)
                existing.limit_reason = item.get("reason", "")
                existing.reason_tags = item.get("limit_type", "")
                existing.source_update_time = datetime.utcnow()
                self.db.add(existing)
                count += 1
            self.db.commit()
            return count

        return self._run("collect_limit_up_daily", _do)

    def update_watch_daily_kline(self, trade_date: date) -> ConfigTaskLog:
        return self._run("update_watch_daily_kline", lambda: 0)

    def update_watch_15m_kline(self, trade_date: date) -> ConfigTaskLog:
        return self._run("update_watch_15m_kline", lambda: 0)

    def update_watch_prices(self, trade_date: date) -> ConfigTaskLog:
        def _do() -> int:
            provider = ProviderFactory.create()
            if not hasattr(provider, "get_stock_quote"):
                return 0

            by_code: dict[str, str] = {}
            for stock_code, stock_name in self.db.query(WatchPool.stock_code, WatchPool.stock_name).filter(WatchPool.active.is_(True)).all():
                if stock_code:
                    by_code.setdefault(stock_code, stock_name or "")
            for stock_code, stock_name in self.db.query(WatchSignal.stock_code, WatchSignal.stock_name).distinct().all():
                if stock_code:
                    by_code.setdefault(stock_code, stock_name or "")
            for stock_code, stock_name in self.db.query(WatchTrade.stock_code, WatchTrade.stock_name).filter(WatchTrade.trade_status.in_(["open", "holding"])).distinct().all():
                if stock_code:
                    by_code.setdefault(stock_code, stock_name or "")

            affected = 0
            now = datetime.utcnow()
            for stock_code, stock_name in by_code.items():
                quote = provider.get_stock_quote(stock_code) or {}
                price = quote.get("price")
                change_pct = quote.get("change_pct")
                if price is None and change_pct is None:
                    continue
                row = self.db.query(MktStockQuote).filter(MktStockQuote.stock_code == stock_code).first()
                if not row:
                    row = MktStockQuote(stock_code=stock_code)
                    self.db.add(row)
                row.stock_name = stock_name or row.stock_name or ""
                row.latest_price = price
                row.change_pct = change_pct
                row.source = quote.get("source") or provider.__class__.__name__
                row.source_update_time = now
                affected += 1
            self.db.commit()
            return affected

        return self._run("update_watch_prices", _do)

    def scan_watch_signals(self, trade_date: date) -> ConfigTaskLog:
        from app.services.signal_engine import SignalEngine

        return self._run("scan_watch_signals", lambda: len(SignalEngine(self.db).scan()))

    def scan_watch_rules(self, trade_date: date) -> ConfigTaskLog:
        def _do() -> int:
            from app.rule_executors import RuleContext, get_executor
            from app.services.notification import NotificationService
            from app.services.kline import KlineService

            kline_service = KlineService(self.db)
            notification_service = NotificationService()
            provider = ProviderFactory.create()
            notification_errors: list[str] = []
            rows = (
                self.db.query(WatchPool)
                .filter(
                    WatchPool.active.is_(True),
                    WatchPool.system_stage == "observe",
                    WatchPool.trading_system_code.isnot(None),
                    WatchPool.trading_system_code != "",
                )
                .all()
            )
            if not rows:
                return 0

            quote_map = {
                row.stock_code: row.latest_price
                for row in self.db.query(MktStockQuote)
                .filter(MktStockQuote.stock_code.in_([item.stock_code for item in rows]))
                .all()
            }

            def _provider_5m_bars(stock_code: str) -> list[SimpleNamespace]:
                if not hasattr(provider, "get_intraday_kline"):
                    return []
                start_time = datetime.combine(trade_date, time(9, 30))
                end_time = datetime.combine(trade_date, time(15, 0))
                bars = []
                for item in provider.get_intraday_kline(stock_code, "5m", start_time, end_time) or []:
                    bars.append(
                        SimpleNamespace(
                            close_price=item.get("close"),
                            volume=item.get("volume", 0.0),
                            kline_time=item.get("kline_time") or item.get("trade_time"),
                        )
                    )
                return bars

            def _rule_config(binding: TradingSystemRuleBinding, rule: TradingRuleDefinition, watch: WatchPool) -> dict:
                config = {
                    "binding_id": binding.binding_id,
                    "rule_code": rule.rule_code,
                    "rule_name": rule.rule_name,
                    "rule_type": rule.rule_type,
                    "timeframe": rule.timeframe,
                    "executor_key": rule.executor_key,
                    "required": binding.required,
                    "logic_group": binding.logic_group,
                    "logic_operator": binding.logic_operator,
                    "config_json": binding.config_json or {},
                }
                if rule.executor_key == "macd_bottom_divergence":
                    config["kline_bars"] = (
                        kline_service.get_15m_kline(watch.stock_code, 80)
                        if rule.timeframe == "15m"
                        else _provider_5m_bars(watch.stock_code)
                    )
                elif rule.executor_key == "not_break_price":
                    daily = kline_service.get_daily_kline(watch.stock_code, 5)
                    if daily:
                        latest = daily[-1]
                        config["latest_close"] = latest.close_price
                        config["latest_time"] = datetime.combine(latest.trade_date, datetime.min.time())
                return config

            def _duplicate_exists(watch: WatchPool, rule_code: str, trigger_date: date) -> bool:
                return bool(
                    self.db.query(WatchSignal.signal_id)
                    .filter(
                        WatchSignal.watch_id == watch.id,
                        WatchSignal.rule_code == rule_code,
                        WatchSignal.trigger_date == trigger_date,
                    )
                    .first()
                )

            def _save_signal(watch: WatchPool, rule: TradingRuleDefinition, result) -> int:
                trigger_time = result.trigger_time or datetime.utcnow()
                trigger_date = trigger_time.date() if hasattr(trigger_time, "date") else trade_date
                if _duplicate_exists(watch, rule.rule_code, trigger_date):
                    return 0
                signal = WatchSignal(
                    watch_id=watch.id,
                    stock_code=watch.stock_code,
                    stock_name=watch.stock_name,
                    signal_type="buy",
                    buy_point_type=rule.rule_code,
                    trading_system=watch.trading_system_code or watch.trading_system,
                    trading_system_code=watch.trading_system_code,
                    rule_code=rule.rule_code,
                    rule_type=rule.rule_type,
                    strategy_name=f"rule_executor:{rule.executor_key}",
                    signal_level=result.signal_level or "B",
                    kline_period=rule.timeframe,
                    trigger_time=trigger_time,
                    trigger_date=trigger_date,
                    trigger_price=result.trigger_price,
                    trigger_reason=result.reason,
                    risk_desc=result.risk_desc,
                    signal_status="buy_pending_confirm",
                    user_action="pending",
                    trigger_signature=f"rule:{watch.id}:{rule.rule_code}:{trigger_date.isoformat()}",
                    raw_snapshot=result.snapshot or {},
                    snapshot_json=result.snapshot or {},
                )
                self.db.add(signal)
                self.db.flush()
                watch.latest_signal_id = signal.signal_id
                watch.status = "buy_pending_confirm"
                watch.next_action = "等待人工确认买入"
                notify_result = notification_service.notify_buy_signal(
                    signal,
                    trading_system_name=watch.trading_system_code or watch.trading_system,
                    rule_name=rule.rule_name,
                )
                if notify_result.error:
                    notification_errors.append(f"{watch.stock_code}/{rule.rule_code}: {notify_result.error}")
                return 1

            affected = 0
            for watch in rows:
                bindings = (
                    self.db.query(TradingSystemRuleBinding, TradingRuleDefinition)
                    .join(TradingRuleDefinition, TradingRuleDefinition.rule_code == TradingSystemRuleBinding.rule_code)
                    .filter(
                        TradingSystemRuleBinding.system_code == watch.trading_system_code,
                        TradingSystemRuleBinding.stage == "observe",
                        TradingSystemRuleBinding.enabled.is_(True),
                        TradingRuleDefinition.enabled.is_(True),
                    )
                    .order_by(TradingSystemRuleBinding.sort_order.asc(), TradingSystemRuleBinding.binding_id.asc())
                    .all()
                )
                results = []
                for binding, rule in bindings:
                    if rule.executor_key not in self.SAFE_RULE_EXECUTORS:
                        continue
                    executor = get_executor(rule.executor_key)
                    if executor is None:
                        continue
                    rule_config = _rule_config(binding, rule, watch)
                    context = RuleContext(
                        watch_id=watch.id,
                        stock_code=watch.stock_code,
                        stock_name=watch.stock_name,
                        trading_system_code=watch.trading_system_code,
                        stage=watch.system_stage or "observe",
                        system_params=watch.system_params_json or {},
                        rule_config=rule_config,
                        trade_date=trade_date,
                        latest_price=quote_map.get(watch.stock_code),
                    )
                    result = executor.execute(context)
                    results.append((binding, rule, result))
                    affected += 1
                required_ok = all(result.triggered for binding, _rule, result in results if binding.required)
                if not required_ok:
                    continue
                buy_results = [
                    (binding, rule, result)
                    for binding, rule, result in results
                    if rule.rule_type == "buy_signal" and result.triggered
                ]
                if not buy_results:
                    continue
                for _binding, rule, result in buy_results:
                    affected += _save_signal(watch, rule, result)
            return affected, "; ".join(notification_errors[:5])

        return self._run("scan_watch_rules", _do)

    def scan_trade_rules(self, trade_date: date) -> ConfigTaskLog:
        def _do() -> int | tuple[int, str]:
            from app.rule_executors import RuleContext, get_executor
            from app.services.kline import KlineService
            from app.services.notification import NotificationService

            kline_service = KlineService(self.db)
            notification_service = NotificationService()
            provider = ProviderFactory.create()
            notification_errors: list[str] = []
            trades = (
                self.db.query(WatchTrade)
                .filter(
                    WatchTrade.trade_status.in_(["open", "holding"]),
                    WatchTrade.current_stage == "trading",
                    WatchTrade.trading_system_code.isnot(None),
                    WatchTrade.trading_system_code != "",
                )
                .all()
            )
            if not trades:
                return 0

            quote_map = {
                row.stock_code: row.latest_price
                for row in self.db.query(MktStockQuote)
                .filter(MktStockQuote.stock_code.in_([item.stock_code for item in trades]))
                .all()
            }

            def _provider_bars(stock_code: str, timeframe: str) -> list[SimpleNamespace]:
                if not hasattr(provider, "get_intraday_kline"):
                    return []
                start_time = datetime.combine(trade_date, time(9, 30))
                end_time = datetime.combine(trade_date, time(15, 0))
                return [
                    SimpleNamespace(
                        close_price=item.get("close"),
                        volume=item.get("volume", 0.0),
                        kline_time=item.get("kline_time") or item.get("trade_time"),
                    )
                    for item in provider.get_intraday_kline(stock_code, timeframe, start_time, end_time) or []
                ]

            def _bindings(trade: WatchTrade) -> list[tuple[TradingSystemRuleBinding, TradingRuleDefinition]]:
                active_codes = set(trade.active_sell_rule_codes_json or []) | set(trade.active_stop_rule_codes_json or [])
                query = (
                    self.db.query(TradingSystemRuleBinding, TradingRuleDefinition)
                    .join(TradingRuleDefinition, TradingRuleDefinition.rule_code == TradingSystemRuleBinding.rule_code)
                    .filter(
                        TradingSystemRuleBinding.system_code == trade.trading_system_code,
                        TradingSystemRuleBinding.stage.in_(["trading", "sell", "stop_loss"]),
                        TradingSystemRuleBinding.enabled.is_(True),
                        TradingRuleDefinition.enabled.is_(True),
                    )
                )
                if active_codes:
                    query = query.filter(TradingSystemRuleBinding.rule_code.in_(active_codes))
                return query.order_by(TradingSystemRuleBinding.stage.asc(), TradingSystemRuleBinding.sort_order.asc()).all()

            def _rule_config(binding: TradingSystemRuleBinding, rule: TradingRuleDefinition, trade: WatchTrade) -> dict:
                config = {
                    "binding_id": binding.binding_id,
                    "rule_code": rule.rule_code,
                    "rule_name": rule.rule_name,
                    "rule_type": rule.rule_type,
                    "timeframe": rule.timeframe,
                    "executor_key": rule.executor_key,
                    "required": binding.required,
                    "logic_group": binding.logic_group,
                    "logic_operator": binding.logic_operator,
                    "config_json": binding.config_json or {},
                }
                if rule.executor_key in {"macd_top_divergence", "macd_dead_cross"}:
                    config["kline_bars"] = _provider_bars(trade.stock_code, rule.timeframe)
                elif rule.executor_key == "break_price":
                    daily = kline_service.get_daily_kline(trade.stock_code, 5)
                    if daily:
                        latest = daily[-1]
                        config["latest_close"] = latest.close_price
                        config["latest_time"] = datetime.combine(latest.trade_date, datetime.min.time())
                return config

            def _duplicate_exists(trade: WatchTrade, rule_code: str, trigger_date: date) -> bool:
                return bool(
                    self.db.query(WatchSignal.signal_id)
                    .filter(
                        WatchSignal.related_trade_id == trade.id,
                        WatchSignal.rule_code == rule_code,
                        WatchSignal.trigger_date == trigger_date,
                    )
                    .first()
                )

            def _save_signal(trade: WatchTrade, watch: WatchPool | None, rule: TradingRuleDefinition, result) -> int:
                trigger_time = result.trigger_time or datetime.utcnow()
                trigger_date = trigger_time.date() if hasattr(trigger_time, "date") else trade_date
                if _duplicate_exists(trade, rule.rule_code, trigger_date):
                    return 0
                is_stop = rule.rule_type == "stop_loss"
                signal = WatchSignal(
                    watch_id=trade.watch_id,
                    stock_code=trade.stock_code,
                    stock_name=trade.stock_name,
                    signal_type="risk" if is_stop else "sell",
                    buy_point_type=rule.rule_code,
                    trading_system=trade.trading_system_code or trade.trading_system,
                    trading_system_code=trade.trading_system_code,
                    rule_code=rule.rule_code,
                    rule_type=rule.rule_type,
                    strategy_name=f"rule_executor:{rule.executor_key}",
                    signal_level=result.signal_level or ("S" if is_stop else "B"),
                    kline_period=rule.timeframe,
                    trigger_time=trigger_time,
                    trigger_date=trigger_date,
                    trigger_price=result.trigger_price,
                    trigger_reason=result.reason,
                    risk_desc=result.risk_desc,
                    signal_status="stop_loss_pending" if is_stop else "sell_signal_pending",
                    user_action="pending",
                    related_trade_id=trade.id,
                    trigger_signature=f"trade-rule:{trade.id}:{rule.rule_code}:{trigger_date.isoformat()}",
                    raw_snapshot=result.snapshot or {},
                    snapshot_json=result.snapshot or {},
                )
                self.db.add(signal)
                self.db.flush()
                trade.latest_trade_signal_id = signal.signal_id
                if watch:
                    watch.latest_signal_id = signal.signal_id
                    watch.status = "sell_signal_pending"
                    watch.next_action = "等待人工确认卖出或止损"
                notify_result = notification_service.notify_trade_signal(
                    signal,
                    trading_system_name=trade.trading_system_code or trade.trading_system,
                    rule_name=rule.rule_name,
                )
                if notify_result.error:
                    notification_errors.append(f"{trade.stock_code}/{rule.rule_code}: {notify_result.error}")
                return 1

            affected = 0
            for trade in trades:
                watch = self.db.query(WatchPool).filter(WatchPool.id == trade.watch_id).first() if trade.watch_id else None
                for binding, rule in _bindings(trade):
                    if rule.executor_key not in self.SAFE_RULE_EXECUTORS:
                        continue
                    executor = get_executor(rule.executor_key)
                    if executor is None:
                        continue
                    context = RuleContext(
                        watch_id=trade.watch_id or 0,
                        stock_code=trade.stock_code,
                        stock_name=trade.stock_name,
                        trading_system_code=trade.trading_system_code,
                        stage=trade.current_stage or "trading",
                        system_params=trade.system_params_json or {},
                        rule_config=_rule_config(binding, rule, trade),
                        trade_date=trade_date,
                        latest_price=quote_map.get(trade.stock_code),
                    )
                    result = executor.execute(context)
                    affected += 1
                    if result.triggered:
                        affected += _save_signal(trade, watch, rule, result)
            return affected, "; ".join(notification_errors[:5])

        return self._run("scan_trade_rules", _do)

    def auto_remove_watch_pool(self, trade_date: date) -> ConfigTaskLog:
        def _do() -> int:
            from app.services.kline import KlineService
            from app.services.prd_v1 import PrdWatchPoolService

            kline_service = KlineService(self.db)
            watch_service = PrdWatchPoolService(self.db)
            rows = (
                self.db.query(WatchPool)
                .filter(
                    WatchPool.status == "watching",
                    WatchPool.active.is_(True),
                    WatchPool.auto_remove_price.isnot(None),
                    WatchPool.auto_remove_price > 0,
                )
                .all()
            )
            affected = 0
            for watch in rows:
                has_buy_signal = (
                    self.db.query(WatchSignal.signal_id)
                    .filter(WatchSignal.watch_id == watch.id, WatchSignal.signal_type == "buy")
                    .first()
                )
                if has_buy_signal:
                    continue

                trigger_price = None
                trigger_time = None
                intraday = kline_service.get_15m_kline(watch.stock_code, 32)
                if intraday:
                    latest_15m = intraday[-1]
                    trigger_price = latest_15m.close_price
                    trigger_time = latest_15m.kline_time
                else:
                    daily = kline_service.get_daily_kline(watch.stock_code, 20)
                    if daily:
                        latest_daily = daily[-1]
                        trigger_price = latest_daily.close_price
                        trigger_time = datetime.combine(latest_daily.trade_date, datetime.min.time())

                if trigger_price is None or trigger_time is None:
                    continue
                if watch.created_at and trigger_time <= watch.created_at:
                    continue

                threshold = float(watch.auto_remove_price) * 0.99
                if float(trigger_price) <= threshold:
                    watch_service.transition(
                        watch.id,
                        "removed",
                        f"自动剔除：最新价 {trigger_price} 跌破剔除价 {watch.auto_remove_price} 的 1% 阈值",
                        operator_type="system",
                        operation_type="auto_remove_watch",
                        snapshot={
                            "auto_remove_price": watch.auto_remove_price,
                            "threshold": threshold,
                            "trigger_price": trigger_price,
                            "trigger_time": trigger_time.isoformat(),
                        },
                    )
                    affected += 1
            return affected

        return self._run("auto_remove_watch_pool", _do)

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
