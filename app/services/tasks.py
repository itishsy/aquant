from __future__ import annotations

import json
from datetime import date, datetime
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
    WatchPool,
    WatchSignal,
)
from app.providers.factory import ProviderFactory


def _serialize(data: dict) -> dict:
    return json.loads(json.dumps(data, default=str))


class TaskService:
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

    def _run(self, task_name: str, fn: Callable[[], int]) -> ConfigTaskLog:
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
            affected = fn()
            log.run_status = "success"
            log.affected_rows = affected
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

    def scan_watch_signals(self, trade_date: date) -> ConfigTaskLog:
        from app.services.signal_engine import SignalEngine

        return self._run("scan_watch_signals", lambda: len(SignalEngine(self.db).scan()))

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
