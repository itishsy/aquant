from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import WatchPool, WatchSignal
from app.services.kline import KlineService
from app.strategies.base import StrategyBase
from app.strategies.macd15 import Macd15BullishDivergenceStrategy
from app.strategies.risk import BreakoutFailureStrategy, HighVolumeRiskStrategy


ASSISTANT_NOTE = "仅作为交易辅助，请结合个人交易规则确认。"


# ── Rule Configuration ──────────────────────────────────────────────


@dataclass(frozen=True)
class SignalRule:
    """Centralized configuration for a single signal-generation rule.

    Each rule ties a trading-system to a strategy and its buy-point type.
    Add new rows to ``SIGNAL_RULES`` to extend the scanner without changing
    the engine internals.
    """

    trading_system: str
    strategy_name: str
    buy_point_type: str = ""
    signal_type: str = "buy"
    enabled: bool = True
    only_after_watch_created: bool = True

    def __post_init__(self):
        if not self.buy_point_type:
            object.__setattr__(self, "buy_point_type", self.strategy_name)


# ── Registered rules ─────────────────────────────────────────────────
#
# To add a new trading-system / buy-signal combination:
#   1. Implement the strategy class (subclass ``StrategyBase``).
#   2. Add a ``SignalRule`` row below.
#   3. Add ``register_strategy(YourStrategy())`` in ``SignalEngine.__init__``.
#
# Rules with ``enabled=False`` are skipped at scan time.

SIGNAL_RULES: list[SignalRule] = [
    # ── 突破 ──
    SignalRule(
        trading_system="breakout",
        strategy_name="macd_15m_bullish_divergence",
        buy_point_type="b15_divergence",
        signal_type="buy",
    ),
    SignalRule(
        trading_system="breakout",
        strategy_name="platform_breakout_confirm",
        buy_point_type="platform_breakout_confirm",
        signal_type="buy",
    ),
    # ── 趋势 ──
    SignalRule(
        trading_system="uptrend",
        strategy_name="macd_15m_bullish_divergence",
        buy_point_type="b15_divergence",
        signal_type="buy",
    ),
    SignalRule(
        trading_system="uptrend",
        strategy_name="support_area_buy",
        buy_point_type="support_buy",
        signal_type="buy",
        enabled=False,  # strategy not yet implemented
    ),
    # ── 接力 (暂无策略实现) ──
    # SignalRule(trading_system="relay", strategy_name="...", ...),
    # ── 风控 (独立于交易体系, 对所有体系生效) ──
    SignalRule(
        trading_system="*",
        strategy_name="high_volume_risk",
        signal_type="risk",
        only_after_watch_created=False,
    ),
    SignalRule(
        trading_system="*",
        strategy_name="breakout_failure",
        signal_type="sell",
        only_after_watch_created=False,
    ),
]


# ── Engine ───────────────────────────────────────────────────────────


class SignalEngine:
    """PRD v1 signal scanner: only eligible manual watch-pool stocks can trigger signals.

    All signal rules are configured in ``SIGNAL_RULES``.  Strategies are
    registered by name and looked up at scan time.
    """

    ACTIVE_SCAN_STATUS = "watching"

    def __init__(self, db: Session):
        self.db = db
        self.kline_service = KlineService(db)
        self.strategies: dict[str, StrategyBase] = {}
        self.register_strategy(Macd15BullishDivergenceStrategy())
        self.register_strategy(HighVolumeRiskStrategy())
        self.register_strategy(BreakoutFailureStrategy())

    # ── rule helpers ─────────────────────────────────────────────────

    @classmethod
    def _rules_for_system(cls, trading_system: str | None) -> list[SignalRule]:
        """Return enabled rules matching the given trading system."""
        system = trading_system or ""
        return [
            r
            for r in SIGNAL_RULES
            if r.enabled and (r.trading_system == system or r.trading_system == "*")
        ]

    @classmethod
    def _buy_point_type_for(cls, strategy_name: str) -> str:
        for r in SIGNAL_RULES:
            if r.strategy_name == strategy_name:
                return r.buy_point_type
        return strategy_name

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
            "trading_system": watch_item.trading_system,
            "kline_daily": daily,
            "kline_15m": intraday,
            "data_quality_ok": bool(daily and intraday),
            "watch_created_at": watch_item.created_at,
        }

    def _strategies_for_watch(self, watch_item: WatchPool, requested: str | None = None) -> list[str]:
        """Return the strategy names that should run for this watch item."""
        rules = self._rules_for_system(watch_item.trading_system)
        names = [r.strategy_name for r in rules]
        if requested:
            return [requested] if requested in names else []
        return names

    def _should_skip_before_watch(self, context: dict, signal: dict, trigger_time: datetime) -> bool:
        """Return True if the signal occurred before the watch was created."""
        strategy_name = signal.get("strategy_name", "")
        rule = next((r for r in SIGNAL_RULES if r.strategy_name == strategy_name), None)
        if not rule or not rule.only_after_watch_created:
            return False
        watch_created_at = context.get("watch_created_at")
        if watch_created_at is None:
            return False
        if isinstance(watch_created_at, datetime):
            return trigger_time <= watch_created_at
        # `created_at` may be a date; treat same day as OK
        if hasattr(watch_created_at, "date"):
            return trigger_time.date() < watch_created_at
        return False

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
        trigger_signature: str,
        context: dict,
        signal: dict,
        buy_point_type: str,
    ) -> WatchSignal | None:
        """Dedup by trigger_signature first, then by composite unique key."""
        existing = (
            self.db.query(WatchSignal)
            .filter(WatchSignal.trigger_signature == trigger_signature)
            .first()
        )
        if existing:
            return existing
        trigger_time = signal.get("trigger_time")
        if trigger_time:
            existing = (
                self.db.query(WatchSignal)
                .filter(
                    WatchSignal.watch_id == context["watch_id"],
                    WatchSignal.strategy_name == signal["strategy_name"],
                    WatchSignal.buy_point_type == buy_point_type,
                    WatchSignal.signal_type == signal["signal_type"],
                    WatchSignal.trigger_time == trigger_time,
                )
                .first()
            )
        return existing

    def save_signal(self, context: dict, signal: dict) -> WatchSignal | None:
        signal_type = signal["signal_type"]
        buy_point_type = signal.get("buy_point_type") or self._buy_point_type_for(signal["strategy_name"])
        trigger_time = signal.get("trigger_time") or datetime.utcnow()
        trigger_date = trigger_time.date() if hasattr(trigger_time, "date") else datetime.utcnow().date()
        trigger_signature = signal.get("trigger_signature") or self._trigger_signature(context, signal, buy_point_type)

        # ── only_after_watch_created filter ──
        if self._should_skip_before_watch(context, signal, trigger_time):
            return None
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

        existing = self.deduplicate_signal(trigger_signature, context, signal, buy_point_type)
        if existing:
            return existing

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
            trigger_time=trigger_time,
            trigger_price=signal.get("trigger_price"),
            signal_level=signal["signal_level"],
            signal_status=signal_status,
            user_action="pending",
            buy_point_confirmed=buy_point_confirmed,
            buy_point_confirm_time=trigger_time if buy_point_confirmed else None,
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
