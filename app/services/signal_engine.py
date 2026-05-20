from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import WatchPool, WatchSignal
from app.services.kline import KlineService
from app.strategies.base import StrategyBase
from app.strategies.macd15 import Macd15BullishDivergenceStrategy
from app.strategies.risk import BreakoutFailureStrategy, HighVolumeRiskStrategy


ASSISTANT_NOTE = "仅作为交易辅助，请结合个人交易规则确认。"


class SignalEngine:
    """PRD v1 signal scanner: only eligible manual watch-pool stocks can trigger signals."""

    ACTIVE_SCAN_STATUS = "watching"
    TRADING_SYSTEM_STRATEGIES = {
        "platform_breakout": ["platform_breakout_confirm"],
        "uptrend": ["macd_15m_bullish_divergence", "support_area_buy"],
        "relay": [],
    }
    BUY_POINT_TYPES = {
        "macd_15m_bullish_divergence": "b15_divergence",
        "support_area_buy": "support_buy",
        "platform_breakout_confirm": "platform_breakout_confirm",
    }

    def __init__(self, db: Session):
        self.db = db
        self.kline_service = KlineService(db)
        self.strategies: dict[str, StrategyBase] = {}
        self.register_strategy(Macd15BullishDivergenceStrategy())
        self.register_strategy(HighVolumeRiskStrategy())
        self.register_strategy(BreakoutFailureStrategy())

    def register_strategy(self, strategy: StrategyBase) -> None:
        self.strategies[strategy.name] = strategy

    def build_context(self, watch_item: WatchPool) -> dict:
        daily = self.kline_service.get_daily_kline(watch_item.stock_code, 40)
        intraday = self.kline_service.get_15m_kline(watch_item.stock_code, 64)
        return {
            "watch_id": watch_item.id,
            "stock_code": watch_item.stock_code,
            "stock_name": watch_item.stock_name,
            "sector_name": watch_item.sector_name,
            "in_watch_pool": True,
            "monitor_enabled": watch_item.monitor_enabled,
            "signal_enabled": watch_item.signal_enabled,
            "status": watch_item.status,
            "status": watch_item.status,
            "trading_system": watch_item.trading_system,
            "kline_daily": daily,
            "kline_15m": intraday,
            "data_quality_ok": bool(daily and intraday),
        }

    def _buy_point_type_for(self, strategy_name: str) -> str:
        return self.BUY_POINT_TYPES.get(strategy_name, strategy_name)

    def _strategies_for_watch(self, watch_item: WatchPool, requested: str | None = None) -> list[str]:
        configured = self.TRADING_SYSTEM_STRATEGIES.get(watch_item.trading_system or "", [])
        if requested:
            return [requested] if requested in configured else []
        return configured

    def _trigger_signature(self, context: dict, signal: dict, buy_point_type: str) -> str:
        if signal.get("trigger_signature"):
            return signal["trigger_signature"]
        return ":".join(
            [
                str(context["watch_id"]),
                str(context["stock_code"]),
                str(signal["strategy_name"]),
                str(buy_point_type),
                str(signal.get("trigger_price") or ""),
            ]
        )

    def _status_for_signal(self, signal: dict) -> str:
        if signal.get("signal_status") in {"waiting_buy_point", "buy_pending_confirm", "signal_generated"}:
            return signal["signal_status"]
        if signal.get("buy_point_confirmed") is True:
            return "buy_pending_confirm"
        if signal.get("waiting_buy_point") is True:
            return "waiting_buy_point"
        return "signal_generated"

    def deduplicate_signal(
        self,
        stock_code: str,
        buy_point_type: str,
        signal_type: str,
        trigger_date,
    ) -> WatchSignal | None:
        return (
            self.db.query(WatchSignal)
            .filter(
                WatchSignal.stock_code == stock_code,
                WatchSignal.buy_point_type == buy_point_type,
                WatchSignal.signal_type == signal_type,
                WatchSignal.trigger_date == trigger_date,
            )
            .first()
        )

    def save_signal(self, context: dict, signal: dict) -> WatchSignal | None:
        signal_type = signal["signal_type"]
        buy_point_type = self._buy_point_type_for(signal["strategy_name"])
        trigger_date = datetime.utcnow().date()
        trigger_signature = self._trigger_signature(context, signal, buy_point_type)
        abandoned = (
            self.db.query(WatchSignal)
            .filter(
                WatchSignal.trigger_signature == trigger_signature,
                WatchSignal.abandoned_flag.is_(True),
                WatchSignal.prevent_duplicate_signal.is_(True),
            )
            .first()
        )
        if abandoned:
            return None

        existing = self.deduplicate_signal(context["stock_code"], buy_point_type, signal_type, trigger_date)
        if existing:
            return existing

        now = datetime.utcnow()
        signal_status = self._status_for_signal(signal)
        buy_point_confirmed = bool(signal.get("buy_point_confirmed", False))
        entity = WatchSignal(
            watch_id=context["watch_id"],
            stock_code=context["stock_code"],
            stock_name=context["stock_name"],
            signal_type=signal_type,
            buy_point_type=buy_point_type,
            trading_system=context.get("trading_system"),
            strategy_name=signal["strategy_name"],
            trigger_date=trigger_date,
            trigger_time=now,
            trigger_price=signal.get("trigger_price"),
            signal_level=signal["signal_level"],
            signal_status=signal_status,
            user_action="pending",
            buy_point_confirmed=buy_point_confirmed,
            buy_point_confirm_time=now if buy_point_confirmed else None,
            buy_point_confirm_price=(signal.get("buy_point_confirm_price") or signal.get("trigger_price")) if buy_point_confirmed else None,
            trigger_signature=trigger_signature,
            prevent_duplicate_signal=signal.get("prevent_duplicate_signal", True),
            trigger_reason=f"{signal['trigger_reason']} {ASSISTANT_NOTE}",
            risk_desc=f"{signal.get('risk_desc', '')} {ASSISTANT_NOTE}",
            invalid_condition=signal.get("invalid_condition", "strategy condition is no longer valid"),
            raw_snapshot=signal.get("raw_snapshot", {}),
        )
        self.db.add(entity)
        self.db.flush()

        watch = self.db.query(WatchPool).filter(WatchPool.id == context["watch_id"]).first()
        if watch:
            watch.status = signal_status
            watch.status = signal_status
            watch.latest_signal_id = entity.signal_id
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def scan(self, strategy_name: str | None = None) -> list[WatchSignal]:
        watch_items = (
            self.db.query(WatchPool)
            .filter(
                WatchPool.status == self.ACTIVE_SCAN_STATUS,
                WatchPool.signal_enabled.is_(True),
                WatchPool.monitor_enabled.is_(True),
                WatchPool,
                WatchPool.trading_system.isnot(None),
                WatchPool.trading_system != "",
            )
            .all()
        )

        saved: list[WatchSignal] = []
        for item in watch_items:
            context = self.build_context(item)
            generated = []
            for name in self._strategies_for_watch(item, strategy_name):
                strategy = self.strategies.get(name)
                if not strategy:
                    continue
                signal = strategy.scan(context)
                if signal:
                    generated.append(signal)

            risk_like = [item for item in generated if item["signal_type"] in {"risk", "sell"}]
            for signal in risk_like or generated:
                row = self.save_signal(context, signal)
                if row:
                    saved.append(row)
        return saved
