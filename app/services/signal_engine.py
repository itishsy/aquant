from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import WatchPool, WatchSignal
from app.services.kline import KlineService
from app.strategies.base import StrategyBase
from app.strategies.macd15 import Macd15BullishDivergenceStrategy
from app.strategies.risk import BreakoutFailureStrategy, HighVolumeRiskStrategy


ASSISTANT_NOTE = "仅作为交易辅助，请结合个人交易规则确认。"


class SignalEngine:
    """PRD v1 signal scanner: only manual watch-pool stocks can trigger signals."""

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
            "pool_status": watch_item.pool_status,
            "buy_point_types": watch_item.buy_point_types or [],
            "kline_daily": daily,
            "kline_15m": intraday,
            "data_quality_ok": bool(daily and intraday),
        }

    def _buy_point_type_for(self, strategy_name: str) -> str:
        mapping = {
            "macd_15m_bullish_divergence": "B15 底背离买点",
            "support_area_buy": "支撑买点",
            "platform_breakout_confirm": "平台突破确认买点",
        }
        return mapping.get(strategy_name, strategy_name)

    def deduplicate_signal(
        self,
        stock_code: str,
        buy_point_type: str,
        signal_type: str,
        trigger_date: date,
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

    def save_signal(self, context: dict, signal: dict) -> WatchSignal:
        signal_type = signal["signal_type"]
        buy_point_type = self._buy_point_type_for(signal["strategy_name"])
        trigger_date = datetime.utcnow().date()
        existing = self.deduplicate_signal(context["stock_code"], buy_point_type, signal_type, trigger_date)
        if existing:
            return existing

        entity = WatchSignal(
            watch_id=context["watch_id"],
            stock_code=context["stock_code"],
            stock_name=context["stock_name"],
            signal_type=signal_type,
            buy_point_type=buy_point_type,
            trigger_date=trigger_date,
            trigger_time=datetime.utcnow(),
            trigger_price=signal.get("trigger_price"),
            signal_level=signal["signal_level"],
            signal_status="未处理",
            user_action="未处理",
            trigger_reason=f"{signal['trigger_reason']} {ASSISTANT_NOTE}",
            risk_desc=f"{signal['risk_desc']} {ASSISTANT_NOTE}",
            invalid_condition=signal.get("invalid_condition", "策略条件不再满足"),
            raw_snapshot=signal.get("raw_snapshot", {}),
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def scan(self, strategy_name: str | None = None) -> list[WatchSignal]:
        watch_items = (
            self.db.query(WatchPool)
            .filter(
                WatchPool.pool_status == "观察中",
                WatchPool.monitor_enabled.is_(True),
                WatchPool.is_blacklist.is_(False),
            )
            .all()
        )
        saved: list[WatchSignal] = []
        names = [strategy_name] if strategy_name else list(self.strategies)
        for item in watch_items:
            context = self.build_context(item)
            generated = []
            for name in names:
                strategy = self.strategies.get(name)
                if not strategy:
                    continue
                if strategy.type == "buy" and self._buy_point_type_for(name) not in (item.buy_point_types or []):
                    continue
                signal = strategy.scan(context)
                if signal:
                    generated.append(signal)
            risk_like = [item for item in generated if item["signal_type"] in {"risk", "sell"}]
            for signal in risk_like or generated:
                saved.append(self.save_signal(context, signal))
        return saved
