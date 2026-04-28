from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import CandleSessionLocal
from app.models import MarketDaily, SectorDaily, SignalRecord, StrategyConfig, WatchPool
from app.services.kline import KlineService
from app.strategies.base import StrategyBase
from app.strategies.macd15 import Macd15BullishDivergenceStrategy
from app.strategies.risk import BreakoutFailureStrategy, HighVolumeRiskStrategy


class SignalEngine:
    def __init__(self, db: Session, candle_db: Session | None = None):
        self.db = db
        self.candle_db = candle_db or CandleSessionLocal()
        self._owns_candle_session = candle_db is None
        self.kline_service = KlineService(self.candle_db)
        self.strategies: dict[str, StrategyBase] = {}
        self.register_strategy(Macd15BullishDivergenceStrategy())
        self.register_strategy(HighVolumeRiskStrategy())
        self.register_strategy(BreakoutFailureStrategy())

    def register_strategy(self, strategy: StrategyBase) -> None:
        self.strategies[strategy.name] = strategy
        config = self.db.query(StrategyConfig).filter(StrategyConfig.strategy_name == strategy.name).first()
        if not config:
            self.db.add(
                StrategyConfig(
                    strategy_name=strategy.name,
                    strategy_type=strategy.type,
                    enabled=True,
                    params={},
                )
            )
            self.db.commit()

    def build_context(self, watch_item: WatchPool) -> dict:
        market = self.db.query(MarketDaily).order_by(MarketDaily.trade_date.desc()).first()
        sector = (
            self.db.query(SectorDaily)
            .filter(SectorDaily.trade_date == market.trade_date, SectorDaily.sector_name == watch_item.sector_name)
            .first()
            if market and watch_item.sector_name
            else None
        )
        daily = self.kline_service.get_daily_kline(watch_item.stock_code, 40)
        intraday = self.kline_service.get_15m_kline(watch_item.stock_code, 64)
        return {
            "stock_code": watch_item.stock_code,
            "stock_name": watch_item.stock_name,
            "sector_name": watch_item.sector_name,
            "sector_type": sector.sector_type if sector else "轮动板块",
            "market_status": market.market_status if market else "震荡",
            "in_watch_pool": True,
            "kline_daily": daily,
            "kline_15m": intraday,
            "data_quality_ok": bool(daily and intraday),
            "high_volume_distribution": False,
            "daily_trend_broken": False,
        }

    def apply_market_filter(self, signal: dict) -> bool:
        if signal["signal_type"] == "buy" and signal["raw_snapshot"]["market_status"] in {"退潮", "冰点"}:
            return False
        return True

    def apply_risk_filter(self, signals: list[dict]) -> list[dict]:
        risk_like = [item for item in signals if item["signal_type"] in {"risk", "sell"}]
        return risk_like if risk_like else signals

    def save_signal(self, context: dict, signal: dict) -> SignalRecord:
        entity = SignalRecord(
            stock_code=context["stock_code"],
            stock_name=context["stock_name"],
            sector_name=context.get("sector_name"),
            signal_type=signal["signal_type"],
            signal_text=signal["signal_text"],
            strategy_name=signal["strategy_name"],
            signal_level=signal["signal_level"],
            trigger_time=datetime.utcnow(),
            current_price=context["kline_15m"][-1].close if context["kline_15m"] else context["kline_daily"][-1].close,
            trigger_reason=signal["trigger_reason"],
            risk_desc=signal["risk_desc"],
            stop_loss_price=signal.get("stop_loss_price"),
            invalid_condition=signal["invalid_condition"],
            market_status=context["market_status"],
            raw_snapshot=signal["raw_snapshot"],
            valid=True,
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def scan(self, strategy_name: str | None = None) -> list[SignalRecord]:
        watch_items = self.db.query(WatchPool).filter(WatchPool.active.is_(True), WatchPool.is_blacklist.is_(False)).all()
        saved = []
        for item in watch_items:
            context = self.build_context(item)
            configs = self.db.query(StrategyConfig).filter(StrategyConfig.enabled.is_(True)).all()
            enabled_names = {config.strategy_name for config in configs}
            names = [strategy_name] if strategy_name else [name for name in self.strategies if name in enabled_names]
            generated = []
            for name in names:
                strategy = self.strategies[name]
                signal = strategy.scan(context)
                if signal and self.apply_market_filter(signal):
                    generated.append(signal)
            for signal in self.apply_risk_filter(generated):
                saved.append(self.save_signal(context, signal))
                item.last_signal_type = signal["signal_type"]
            self.db.commit()
        if self._owns_candle_session:
            self.candle_db.close()
        return saved
