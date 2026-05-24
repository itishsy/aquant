from datetime import date, timedelta

from app.models import ConfigTask, WatchPool, WatchSignal, WatchTrade
from app.services.kline_repository import KlineRepository
from app.services.prd_v1 import SeedService
from app.services.tasks import TaskService


def test_seed_includes_scan_trade_rules_task(db_session):
    SeedService(db_session).init_defaults()

    task = db_session.query(ConfigTask).filter(ConfigTask.task_name == "scan_trade_rules").first()

    assert task is not None
    assert task.owner_module == "signal"
    assert task.task_type == "scheduled"


def test_scan_trade_rules_generates_platform_break_support_signal(db_session):
    SeedService(db_session).init_defaults()
    watch = WatchPool(
        stock_code="603019.SH",
        stock_name="中科曙光",
        status="trading",
        active=True,
        trading_system="platform_breakout",
        trading_system_code="platform_breakout",
        system_stage="trading",
        system_params_json={"platform_support_price": 23.0},
    )
    db_session.add(watch)
    db_session.flush()
    trade = WatchTrade(
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        trade_status="open",
        trading_system="platform_breakout",
        trading_system_code="platform_breakout",
        system_params_json={"platform_support_price": 23.0},
        active_stop_rule_codes_json=["break_platform_support"],
        active_sell_rule_codes_json=[],
        current_stage="trading",
        first_buy_price=25.0,
        average_buy_price=25.0,
        total_buy_amount=100,
        remaining_amount=100,
    )
    db_session.add(trade)
    KlineRepository(db_session).upsert_rows(
        "603019.SH",
        "daily",
        [
            {
                "trade_date": date(2026, 5, 20) + timedelta(days=idx),
                "open": 23.2,
                "high": 23.4,
                "low": 22.0,
                "close": 22.5,
                "volume": 100000,
                "amount": 2250000,
            }
            for idx in range(5)
        ],
        "test",
    )
    db_session.commit()

    log = TaskService(db_session).scan_trade_rules(date(2026, 5, 24))
    signal = db_session.query(WatchSignal).filter(WatchSignal.related_trade_id == trade.id).first()

    assert log.run_status == "success"
    assert signal is not None
    assert signal.signal_type == "risk"
    assert signal.rule_type == "stop_loss"
    assert signal.rule_code == "break_platform_support"
    assert signal.signal_status == "stop_loss_pending"
    assert signal.related_trade_id == trade.id
    assert signal.notification_sent is False
    assert signal.notification_error
    assert "email notification is disabled" in (log.error_message or "")

    second = TaskService(db_session).scan_trade_rules(date(2026, 5, 24))
    assert second.run_status == "success"
    assert db_session.query(WatchSignal).filter(WatchSignal.related_trade_id == trade.id).count() == 1


def test_scan_trade_rules_does_not_call_provider_when_data_missing(db_session, monkeypatch):
    SeedService(db_session).init_defaults()
    trade = WatchTrade(
        stock_code="603019.SH",
        stock_name="中科曙光",
        trade_status="open",
        trading_system="platform_breakout",
        trading_system_code="platform_breakout",
        system_params_json={"platform_support_price": 23.0},
        active_stop_rule_codes_json=["break_platform_support"],
        active_sell_rule_codes_json=[],
        current_stage="trading",
    )
    db_session.add(trade)
    db_session.commit()

    def _raise_provider():
        raise AssertionError("provider must not be called during scan_trade_rules")

    monkeypatch.setattr("app.services.tasks.ProviderFactory.create", _raise_provider)
    log = TaskService(db_session).scan_trade_rules(date(2026, 5, 24))

    assert log.run_status == "success"
    assert db_session.query(WatchSignal).count() == 0
    assert "Need" in (log.error_message or "")
