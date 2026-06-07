from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    MktStockQuote,
    TradingRuleDefinition,
    TradingSystemDefinition,
    WatchPool,
    WatchSignal,
    WatchTrade,
    WatchTradeExecution,
)
from app.services.prd_v1 import PrdWatchPoolService


PENDING_SIGNAL_STATUSES = {
    "buy_pending_confirm",
    "sell_signal_pending",
    "stop_loss_pending",
    "observe_risk_pending",
    "observe_invalid_pending",
    "observe_remove_pending",
}
OPEN_TRADE_STATUSES = {"open", "holding"}
TERMINAL_STATUSES = PrdWatchPoolService.TERMINAL_STATUSES

STATUS_NAMES = {
    "watching": "观察中",
    "signal_generated": "已出信号",
    "waiting_buy_point": "等待买点",
    "buy_pending_confirm": "买入待确认",
    "trading": "交易中",
    "sell_signal_pending": "卖出待处理",
    "sell_delayed": "卖出延后",
    "sold": "已卖出",
    "pending_review": "待复盘",
    "archived": "已归档",
    "invalid": "已失效",
    "blacklist": "黑名单",
    "removed": "已剔除",
}

EXECUTION_TYPE_NAMES = {
    "buy": "买入",
    "sell": "卖出",
    "stop_loss": "止损",
    "take_profit": "止盈",
}


class WatchOverviewService:
    def __init__(self, db: Session, now: datetime | None = None):
        self.db = db
        self.settings = get_settings()
        self.local_now = self._local_now(now)
        self.local_today = self.local_now.date()

    def overview(
        self,
        *,
        keyword: str | None = None,
        trading_system: str | None = None,
        status: str | None = None,
        include_terminal: bool = True,
    ) -> dict:
        watches = self._watch_rows(keyword, trading_system, status, include_terminal)
        if not watches:
            return {
                "summary": {
                    "total": 0,
                    "active_total": 0,
                    "terminal_total": 0,
                    "today_signal_count": self._today_signal_count(),
                    "today_trade_count": self._today_trade_count(),
                },
                "items": [],
            }

        watch_ids = [row.id for row in watches]
        stock_codes = sorted({row.stock_code for row in watches})
        quotes = self._quote_map(stock_codes)
        system_names = self._system_name_map(watches)
        signals = self._latest_signals(watch_ids, stock_codes)
        trades = self._related_open_trades(watch_ids, stock_codes)
        rule_names = self._rule_name_map(signals)

        latest_signals = self._latest_signal_by_watch(watches, signals)
        active_trades = self._active_trade_by_watch(watches, trades)
        latest_trade_signals = self._latest_trade_signal_by_trade_ids([row.id for row in active_trades.values()])

        items = [
            self._overview_item(
                watch,
                quotes.get(watch.stock_code),
                system_names.get(watch.trading_system_code or watch.trading_system or ""),
                latest_signals.get(watch.id),
                active_trades.get(watch.id),
                latest_trade_signals,
                rule_names,
            )
            for watch in watches
        ]
        items.sort(key=self._item_sort_key)
        return {
            "summary": {
                "total": len(items),
                "active_total": sum(1 for row in watches if row.active),
                "terminal_total": sum(1 for row in watches if self._is_terminal(row)),
                "today_signal_count": self._today_signal_count(),
                "today_trade_count": self._today_trade_count(),
            },
            "items": items,
        }

    def get_watch(self, watch_id: int) -> WatchPool | None:
        return self.db.query(WatchPool).filter(WatchPool.id == watch_id).first()

    def signal_rows(self, watch: WatchPool) -> list[WatchSignal]:
        rows = (
            self.db.query(WatchSignal)
            .filter(
                or_(
                    WatchSignal.watch_id == watch.id,
                    (WatchSignal.watch_id.is_(None)) & (WatchSignal.stock_code == watch.stock_code),
                )
            )
            .order_by(WatchSignal.trigger_time.desc(), WatchSignal.signal_id.desc())
            .all()
        )
        return self._dedupe(rows, "signal_id")

    def trade_records(self, watch: WatchPool) -> list[dict]:
        trades = (
            self.db.query(WatchTrade)
            .filter(
                or_(
                    WatchTrade.watch_id == watch.id,
                    (WatchTrade.watch_id.is_(None)) & (WatchTrade.stock_code == watch.stock_code),
                )
            )
            .order_by(WatchTrade.created_at.desc(), WatchTrade.id.desc())
            .all()
        )
        trades = self._dedupe(trades, "id")
        if not trades:
            return []

        trade_ids = [row.id for row in trades]
        executions = (
            self.db.query(WatchTradeExecution)
            .filter(WatchTradeExecution.trade_id.in_(trade_ids))
            .order_by(WatchTradeExecution.execution_time.desc(), WatchTradeExecution.id.desc())
            .all()
        )
        executions_by_trade: dict[int, list[WatchTradeExecution]] = {}
        for execution in executions:
            executions_by_trade.setdefault(execution.trade_id, []).append(execution)

        records: list[dict] = []
        for trade in trades:
            trade_executions = executions_by_trade.get(trade.id, [])
            if trade_executions:
                records.extend(self._execution_record(execution, trade) for execution in trade_executions)
            else:
                records.append(self._trade_summary_record(trade))
        records.sort(key=lambda row: (row["record_time"] or datetime.min, row["trade_id"]), reverse=True)
        return records

    def _watch_rows(
        self,
        keyword: str | None,
        trading_system: str | None,
        status: str | None,
        include_terminal: bool,
    ) -> list[WatchPool]:
        query = self.db.query(WatchPool)
        if status:
            query = query.filter(WatchPool.status == status)
        elif not include_terminal:
            query = query.filter(WatchPool.active.is_(True))
        if trading_system:
            query = query.filter(
                or_(
                    WatchPool.trading_system == trading_system,
                    WatchPool.trading_system_code == trading_system,
                )
            )
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    WatchPool.stock_code.ilike(like),
                    WatchPool.stock_name.ilike(like),
                    WatchPool.entry_reason.ilike(like),
                )
            )
        return query.order_by(WatchPool.id.desc()).all()

    def _latest_signals(self, watch_ids: list[int], stock_codes: list[str]) -> list[WatchSignal]:
        direct_ranked = (
            self.db.query(
                WatchSignal.signal_id.label("signal_id"),
                func.row_number()
                .over(
                    partition_by=WatchSignal.watch_id,
                    order_by=(WatchSignal.trigger_time.desc(), WatchSignal.signal_id.desc()),
                )
                .label("row_no"),
            )
            .filter(WatchSignal.watch_id.in_(watch_ids))
            .subquery()
        )
        legacy_ranked = (
            self.db.query(
                WatchSignal.signal_id.label("signal_id"),
                func.row_number()
                .over(
                    partition_by=WatchSignal.stock_code,
                    order_by=(WatchSignal.trigger_time.desc(), WatchSignal.signal_id.desc()),
                )
                .label("row_no"),
            )
            .filter(WatchSignal.watch_id.is_(None), WatchSignal.stock_code.in_(stock_codes))
            .subquery()
        )
        direct = (
            self.db.query(WatchSignal)
            .join(direct_ranked, direct_ranked.c.signal_id == WatchSignal.signal_id)
            .filter(direct_ranked.c.row_no == 1)
            .all()
        )
        legacy = (
            self.db.query(WatchSignal)
            .join(legacy_ranked, legacy_ranked.c.signal_id == WatchSignal.signal_id)
            .filter(legacy_ranked.c.row_no == 1)
            .all()
        )
        return direct + legacy

    def _related_open_trades(self, watch_ids: list[int], stock_codes: list[str]) -> list[WatchTrade]:
        return (
            self.db.query(WatchTrade)
            .filter(
                WatchTrade.trade_status.in_(OPEN_TRADE_STATUSES),
                or_(
                    WatchTrade.watch_id.in_(watch_ids),
                    (WatchTrade.watch_id.is_(None)) & (WatchTrade.stock_code.in_(stock_codes)),
                )
            )
            .order_by(WatchTrade.created_at.desc(), WatchTrade.id.desc())
            .all()
        )

    def _quote_map(self, stock_codes: list[str]) -> dict[str, MktStockQuote]:
        rows = self.db.query(MktStockQuote).filter(MktStockQuote.stock_code.in_(stock_codes)).all()
        return {row.stock_code: row for row in rows}

    def _system_name_map(self, watches: list[WatchPool]) -> dict[str, str]:
        codes = sorted({row.trading_system_code or row.trading_system for row in watches if row.trading_system_code or row.trading_system})
        if not codes:
            return {}
        rows = self.db.query(TradingSystemDefinition).filter(TradingSystemDefinition.system_code.in_(codes)).all()
        return {row.system_code: row.system_name for row in rows}

    def _rule_name_map(self, signals: list[WatchSignal]) -> dict[str, str]:
        codes = sorted({row.rule_code or row.buy_point_type for row in signals if row.rule_code or row.buy_point_type})
        if not codes:
            return {}
        rows = self.db.query(TradingRuleDefinition).filter(TradingRuleDefinition.rule_code.in_(codes)).all()
        return {row.rule_code: row.rule_name for row in rows}

    def _latest_signal_by_watch(self, watches: list[WatchPool], signals: list[WatchSignal]) -> dict[int, WatchSignal]:
        watch_ids = {watch.id for watch in watches}
        newest_watch_by_code: dict[str, WatchPool] = {}
        for watch in sorted(watches, key=lambda row: (row.created_at or datetime.min, row.id), reverse=True):
            newest_watch_by_code.setdefault(watch.stock_code, watch)

        result = {row.watch_id: row for row in signals if row.watch_id in watch_ids}
        for row in signals:
            if row.watch_id is not None:
                continue
            watch = newest_watch_by_code.get(row.stock_code)
            if watch and watch.id not in result:
                result[watch.id] = row
        return result

    def _active_trade_by_watch(self, watches: list[WatchPool], trades: list[WatchTrade]) -> dict[int, WatchTrade]:
        watch_ids = {watch.id for watch in watches}
        newest_watch_by_code: dict[str, WatchPool] = {}
        for watch in sorted(watches, key=lambda row: (row.created_at or datetime.min, row.id), reverse=True):
            newest_watch_by_code.setdefault(watch.stock_code, watch)
        result: dict[int, WatchTrade] = {}
        for trade in sorted(trades, key=lambda row: (row.created_at or datetime.min, row.id), reverse=True):
            if trade.watch_id in watch_ids:
                result.setdefault(trade.watch_id, trade)
        for trade in sorted(trades, key=lambda row: (row.created_at or datetime.min, row.id), reverse=True):
            if trade.watch_id is not None:
                continue
            watch = newest_watch_by_code.get(trade.stock_code)
            if watch and watch.id not in result:
                result[watch.id] = trade
        return result

    def _latest_trade_signal_by_trade_ids(self, trade_ids: list[int]) -> dict[int, WatchSignal]:
        if not trade_ids:
            return {}
        signals = (
            self.db.query(WatchSignal)
            .filter(WatchSignal.related_trade_id.in_(trade_ids))
            .order_by(WatchSignal.trigger_time.desc(), WatchSignal.signal_id.desc())
            .all()
        )
        result: dict[int, WatchSignal] = {}
        for signal in signals:
            if signal.related_trade_id is not None:
                result.setdefault(signal.related_trade_id, signal)
        return result

    def _overview_item(
        self,
        watch: WatchPool,
        quote: MktStockQuote | None,
        system_name: str | None,
        latest_signal: WatchSignal | None,
        active_trade: WatchTrade | None,
        latest_trade_signals: dict[int, WatchSignal],
        rule_names: dict[str, str],
    ) -> dict:
        group, priority, sort_time = self._display_group(watch, latest_signal, active_trade, latest_trade_signals)
        rule_code = latest_signal.rule_code or latest_signal.buy_point_type if latest_signal else None
        return {
            "watch_id": watch.id,
            "stock_code": watch.stock_code,
            "stock_name": watch.stock_name,
            "latest_price": quote.latest_price if quote else None,
            "change_pct": quote.change_pct if quote else None,
            "sector_name": watch.sector_name,
            "entry_date": watch.added_trade_date or (watch.created_at.date() if watch.created_at else None),
            "entry_source": watch.entry_source,
            "trading_system_code": watch.trading_system_code or watch.trading_system,
            "trading_system_name": system_name or watch.trading_system_code or watch.trading_system,
            "status": watch.status,
            "status_name": self._status_name(watch, active_trade),
            "system_stage": watch.system_stage,
            "display_group": group,
            "sort_priority": priority,
            "sort_time": sort_time,
            "card_tone": group,
            "latest_signal": self._latest_signal_payload(latest_signal, rule_names.get(rule_code or "")),
            "active_trade": self._active_trade_payload(active_trade),
        }

    def _display_group(
        self,
        watch: WatchPool,
        latest_signal: WatchSignal | None,
        active_trade: WatchTrade | None,
        latest_trade_signals: dict[int, WatchSignal],
    ) -> tuple[str, int, datetime | None]:
        if active_trade:
            trade_signal = latest_trade_signals.get(active_trade.id)
            return "trading", 10, (trade_signal.trigger_time if trade_signal else None) or active_trade.updated_at or active_trade.created_at
        if latest_signal and latest_signal.trigger_date == self.local_today:
            priority = 20 if latest_signal.signal_status in PENDING_SIGNAL_STATUSES else 30
            return "today_signal", priority, latest_signal.trigger_time
        if self._is_terminal(watch):
            return "terminal", 90, watch.removed_at or watch.updated_at or watch.created_at
        return "watching", 40, watch.created_at

    @staticmethod
    def _latest_signal_payload(signal: WatchSignal | None, rule_name: str | None) -> dict | None:
        if not signal:
            return None
        rule_code = signal.rule_code or signal.buy_point_type
        return {
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type,
            "signal_status": signal.signal_status,
            "rule_code": rule_code,
            "rule_name": rule_name or rule_code,
            "trigger_time": signal.trigger_time,
        }

    @staticmethod
    def _active_trade_payload(trade: WatchTrade | None) -> dict | None:
        if not trade:
            return None
        return {
            "trade_id": trade.id,
            "trade_status": trade.trade_status,
            "target_price": trade.target_price,
            "stop_loss_price": trade.stop_loss_price,
            "current_stage": trade.current_stage,
        }

    @staticmethod
    def _item_sort_key(item: dict) -> tuple:
        sort_time = item.get("sort_time") or datetime.min
        return item["sort_priority"], -sort_time.timestamp() if sort_time != datetime.min else float("inf"), -item["watch_id"]

    @staticmethod
    def _status_name(watch: WatchPool, active_trade: WatchTrade | None) -> str:
        if active_trade:
            return "交易中"
        if not watch.monitor_enabled or not watch.signal_enabled:
            return "监控暂停"
        return STATUS_NAMES.get(watch.status, watch.status or "-")

    @staticmethod
    def _is_terminal(watch: WatchPool) -> bool:
        return not watch.active or watch.status in TERMINAL_STATUSES

    def _today_signal_count(self) -> int:
        return self.db.query(WatchSignal).filter(WatchSignal.trigger_date == self.local_today).count()

    def _today_trade_count(self) -> int:
        start_utc, end_utc = self._utc_day_bounds(self.local_today)
        return (
            self.db.query(WatchTradeExecution)
            .filter(
                WatchTradeExecution.execution_time >= start_utc,
                WatchTradeExecution.execution_time < end_utc,
            )
            .count()
        )

    @staticmethod
    def _execution_record(execution: WatchTradeExecution, trade: WatchTrade) -> dict:
        return {
            "record_type": "execution",
            "record_time": execution.execution_time,
            "execution_id": execution.id,
            "trade_id": trade.id,
            "execution_type": execution.execution_type,
            "execution_type_name": EXECUTION_TYPE_NAMES.get(execution.execution_type, execution.execution_type),
            "execution_reason": execution.execution_reason,
            "execution_time": execution.execution_time,
            "execution_price": execution.execution_price,
            "execution_amount": execution.execution_amount,
            "pnl_amount": execution.pnl_amount,
            "pnl_ratio": execution.pnl_ratio,
            "trade_status": trade.trade_status,
        }

    @staticmethod
    def _trade_summary_record(trade: WatchTrade) -> dict:
        record_time = trade.first_buy_time or trade.closed_at or trade.created_at
        return {
            "record_type": "trade_summary",
            "record_time": record_time,
            "execution_id": None,
            "trade_id": trade.id,
            "execution_type": "trade",
            "execution_type_name": "交易记录",
            "execution_reason": trade.buy_reason or trade.close_reason or "",
            "execution_time": record_time,
            "execution_price": trade.average_buy_price or trade.first_buy_price,
            "execution_amount": trade.total_buy_amount,
            "pnl_amount": trade.pnl_amount,
            "pnl_ratio": trade.pnl_ratio,
            "trade_status": trade.trade_status,
        }

    @staticmethod
    def _dedupe(rows: list, id_attr: str) -> list:
        result = []
        seen = set()
        for row in rows:
            row_id = getattr(row, id_attr)
            if row_id not in seen:
                seen.add(row_id)
                result.append(row)
        return result

    def _local_now(self, value: datetime | None) -> datetime:
        zone = ZoneInfo(self.settings.timezone)
        if value is None:
            return datetime.now(zone)
        if value.tzinfo is None:
            return value.replace(tzinfo=zone)
        return value.astimezone(zone)

    def _utc_day_bounds(self, value: date) -> tuple[datetime, datetime]:
        zone = ZoneInfo(self.settings.timezone)
        start_local = datetime.combine(value, time.min, tzinfo=zone)
        end_local = start_local + timedelta(days=1)
        start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
        return start_utc, end_utc
