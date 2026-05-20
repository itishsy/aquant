from __future__ import annotations

from datetime import date, datetime

from app.models import WatchPool, WatchSignal
from app.services.signal_engine import SignalEngine
from app.strategies.base import StrategyBase


class AlwaysSignalStrategy(StrategyBase):
    name = "platform_breakout_confirm"
    type = "buy"

    def __init__(self, signature: str = "sig-platform-breakout", status: str = "buy_pending_confirm"):
        self.signature = signature
        self.status = status

    def validate_preconditions(self, context: dict) -> bool:
        return True

    def generate_signal(self, context: dict) -> dict:
        return {
            "signal_type": "buy",
            "strategy_name": self.name,
            "signal_level": "A",
            "trigger_price": 10.0,
            "trigger_reason": "buy watch signal",
            "risk_desc": "risk reminder",
            "signal_status": self.status,
            "buy_point_confirmed": self.status == "buy_pending_confirm",
            "trigger_signature": self.signature,
            "raw_snapshot": {"stock_code": context["stock_code"]},
        }


def _watch(**overrides) -> WatchPool:
    row = WatchPool(
        stock_code="000001.SZ",
        stock_name="Ping An",
        pool_status="watching",
        waiting="watching",
        trading_system="platform_breakout",
        signal_enabled=True,
        monitor_enabled=True,
        
        active=True,
        buy_point_types=["platform_breakout_confirm"],
        reason="manual",
        entry_reason="manual",
        key_observe_price=10.0,
        invalid_condition="close below 9",
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def test_signal_engine_does_not_generate_without_watch_pool(db_session):
    engine = SignalEngine(db_session)
    engine.register_strategy(AlwaysSignalStrategy())
    assert engine.scan() == []
    assert db_session.query(WatchSignal).count() == 0


def test_signal_engine_does_not_generate_when_monitor_disabled(db_session):
    db_session.add(_watch(signal_enabled=False, monitor_enabled=False))
    db_session.commit()

    engine = SignalEngine(db_session)
    engine.register_strategy(AlwaysSignalStrategy())
    assert engine.scan() == []
    assert db_session.query(WatchSignal).count() == 0


def test_signal_engine_does_not_regenerate_abandoned_duplicate(db_session):
    watch = _watch()
    db_session.add(watch)
    db_session.flush()
    db_session.add(
        WatchSignal(
            watch_id=watch.id,
            stock_code=watch.stock_code,
            stock_name=watch.stock_name,
            signal_type="buy",
            buy_point_type="platform_breakout_confirm",
            trading_system="platform_breakout",
            strategy_name="platform_breakout_confirm",
            signal_level="A",
            signal_status="abandoned",
            trigger_date=date.today(),
            trigger_time=datetime.utcnow(),
            trigger_signature="same-trigger",
            abandoned_flag=True,
            prevent_duplicate_signal=True,
        )
    )
    db_session.commit()

    engine = SignalEngine(db_session)
    engine.register_strategy(AlwaysSignalStrategy(signature="same-trigger"))
    assert engine.scan() == []
    assert db_session.query(WatchSignal).count() == 1


def test_signal_engine_updates_watch_status_after_signal_generated(db_session):
    watch = _watch()
    db_session.add(watch)
    db_session.commit()

    engine = SignalEngine(db_session)
    engine.register_strategy(AlwaysSignalStrategy(status="buy_pending_confirm"))
    rows = engine.scan()

    assert len(rows) == 1
    signal = rows[0]
    assert signal.trading_system == "platform_breakout"
    assert signal.buy_point_confirmed is True
    assert signal.trigger_signature == "sig-platform-breakout"

    db_session.refresh(watch)
    assert watch.status == "buy_pending_confirm"
    assert watch.status == "buy_pending_confirm"
    assert watch.latest_signal_id == signal.signal_id
