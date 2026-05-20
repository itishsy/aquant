from __future__ import annotations

from datetime import date, datetime, timedelta

from app.models import WatchPool, WatchSignal
from app.services.signal_engine import SignalEngine
from app.strategies.base import StrategyBase


class AlwaysSignalStrategy(StrategyBase):
    name = "platform_breakout_confirm"
    type = "buy"

    def __init__(
        self,
        signature: str = "sig-platform-breakout",
        status: str = "buy_pending_confirm",
        trigger_time: datetime | None = None,
        buy_point_type: str | None = None,
    ):
        self.signature = signature
        self.status = status
        self.trigger_time = trigger_time
        self.buy_point_type = buy_point_type

    def validate_preconditions(self, context: dict) -> bool:
        return True

    def generate_signal(self, context: dict) -> dict:
        payload: dict = {
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
        if self.trigger_time is not None:
            payload["trigger_time"] = self.trigger_time
        if self.buy_point_type is not None:
            payload["buy_point_type"] = self.buy_point_type
        return payload


def _watch(**overrides) -> WatchPool:
    row = WatchPool(
        stock_code="000001.SZ",
        stock_name="Ping An",
        status="watching",
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
    assert watch.latest_signal_id == signal.signal_id


def test_signal_engine_stores_strategy_trigger_time_and_buy_point_type(db_session):
    """trigger_time from strategy is stored; trigger_date is derived from it."""
    watch = _watch(created_at=datetime(2026, 5, 19, 0, 0, 0))
    db_session.add(watch)
    db_session.commit()

    strategy_time = datetime(2026, 5, 20, 10, 30, 0)  # after watch creation
    engine = SignalEngine(db_session)
    engine.register_strategy(
        AlwaysSignalStrategy(
            signature="sig-with-time",
            status="signal_generated",
            trigger_time=strategy_time,
            buy_point_type="b15_divergence",
        )
    )
    rows = engine.scan()

    assert len(rows) == 1
    signal = rows[0]
    assert signal.trigger_time == strategy_time
    assert signal.trigger_date == strategy_time.date()
    assert signal.buy_point_type == "b15_divergence"
    assert signal.trigger_signature == "sig-with-time"


def test_signal_engine_fallback_trigger_time_when_strategy_omits_it(db_session):
    """Old strategies that do not return trigger_time still work."""
    watch = _watch()
    db_session.add(watch)
    db_session.commit()

    engine = SignalEngine(db_session)
    engine.register_strategy(AlwaysSignalStrategy(signature="no-time", trigger_time=None))
    rows = engine.scan()

    assert len(rows) == 1
    signal = rows[0]
    assert signal.trigger_time is not None  # fallback to utcnow
    assert signal.trigger_date == signal.trigger_time.date()


def test_signal_engine_skips_signal_before_watch_created(db_session):
    """Signal with trigger_time <= watch.created_at is filtered out."""
    watch_created = datetime(2026, 5, 20, 14, 0, 0)
    signal_time = datetime(2026, 5, 20, 10, 0, 0)  # earlier than watch creation

    watch = _watch(created_at=watch_created)
    db_session.add(watch)
    db_session.commit()

    engine = SignalEngine(db_session)
    engine.register_strategy(
        AlwaysSignalStrategy(
            signature="early-signal",
            status="signal_generated",
            trigger_time=signal_time,
            buy_point_type="b15_divergence",
        )
    )
    rows = engine.scan()
    assert rows == []
    assert db_session.query(WatchSignal).count() == 0


def test_signal_engine_allows_signal_after_watch_created(db_session):
    """Signal with trigger_time > watch.created_at is saved normally."""
    watch_created = datetime(2026, 5, 20, 10, 0, 0)
    signal_time = datetime(2026, 5, 20, 14, 0, 0)  # after watch creation

    watch = _watch(created_at=watch_created)
    db_session.add(watch)
    db_session.commit()

    engine = SignalEngine(db_session)
    engine.register_strategy(
        AlwaysSignalStrategy(
            signature="late-signal",
            status="signal_generated",
            trigger_time=signal_time,
            buy_point_type="b15_divergence",
        )
    )
    rows = engine.scan()
    assert len(rows) == 1
    assert rows[0].trigger_signature == "late-signal"


def test_signal_engine_allows_fallback_when_rule_not_only_after(db_session):
    """Rules with only_after_watch_created=False always allow the signal."""
    watch_created = datetime(2026, 5, 20, 14, 0, 0)
    signal_time = datetime(2026, 5, 20, 10, 0, 0)  # before watch

    watch = _watch(created_at=watch_created)
    db_session.add(watch)
    db_session.commit()

    # Use a strategy registered under a wildcard rule (only_after_watch_created=False)
    # The AlwaysSignal name is "platform_breakout_confirm" which maps to only_after=True,
    # so we register a strategy matching a wildcard rule name.
    class RiskLikeStrategy(StrategyBase):
        name = "high_volume_risk"
        type = "risk"

        def validate_preconditions(self, context: dict) -> bool:
            return True

        def generate_signal(self, context: dict) -> dict:
            return {
                "signal_type": "risk",
                "strategy_name": self.name,
                "signal_level": "A",
                "trigger_price": 10.0,
                "trigger_time": signal_time,
                "trigger_reason": "risk test",
                "risk_desc": "test risk",
                "trigger_signature": "risk-early",
                "raw_snapshot": {},
            }

    engine = SignalEngine(db_session)
    engine.register_strategy(RiskLikeStrategy())
    rows = engine.scan()
    assert len(rows) == 1
    assert rows[0].trigger_signature == "risk-early"


def test_signal_engine_repeat_scan_does_not_duplicate_same_signature(db_session):
    """Running scan() twice with same trigger_signature produces only one signal."""
    watch = _watch(created_at=datetime(2026, 5, 19, 0, 0, 0))
    db_session.add(watch)
    db_session.commit()

    engine = SignalEngine(db_session)
    engine.register_strategy(
        AlwaysSignalStrategy(
            signature="dedup-sig",
            status="signal_generated",
            trigger_time=datetime(2026, 5, 20, 10, 30, 0),
            buy_point_type="b15_divergence",
        )
    )
    first = engine.scan()
    assert len(first) == 1
    assert db_session.query(WatchSignal).count() == 1

    # Second scan with same signature
    second = engine.scan()
    assert len(second) == 0
    assert db_session.query(WatchSignal).count() == 1


def test_signal_engine_different_signature_generates_new_signal(db_session):
    """Different trigger_signature for same stock produces a new signal."""
    watch = _watch(created_at=datetime(2026, 5, 19, 0, 0, 0))
    db_session.add(watch)
    db_session.commit()

    engine = SignalEngine(db_session)
    engine.register_strategy(AlwaysSignalStrategy(signature="sig-1", trigger_time=datetime(2026, 5, 20, 10, 30, 0)))
    first = engine.scan()
    assert len(first) == 1

    # Reset watch status so second scan still finds it
    db_session.refresh(watch)
    watch.status = "watching"
    db_session.commit()

    # Re-register with different signature (different time = different 15m bar)
    engine.strategies.clear()
    engine.register_strategy(
        AlwaysSignalStrategy(
            signature="sig-2",
            trigger_time=datetime(2026, 5, 20, 11, 0, 0),
            buy_point_type="b15_divergence",
        )
    )
    second = engine.scan()
    assert len(second) == 1
    assert db_session.query(WatchSignal).count() == 2


def test_signal_engine_does_not_skip_when_watch_created_is_old(db_session):
    """Signal before a very old created_at should not be filtered (same day OK)."""
    signal_time = datetime(2026, 5, 20, 10, 0, 0)
    # created_at is on the same day but earlier — trigger_time > created_at, so allowed
    watch = _watch(created_at=datetime(2026, 5, 20, 9, 0, 0))
    db_session.add(watch)
    db_session.commit()

    engine = SignalEngine(db_session)
    engine.register_strategy(
        AlwaysSignalStrategy(
            signature="no-created-at",
            status="signal_generated",
            trigger_time=signal_time,
            buy_point_type="b15_divergence",
        )
    )
    rows = engine.scan()
    assert len(rows) == 1
    assert rows[0].trigger_signature == "no-created-at"
