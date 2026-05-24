from datetime import date

from app.models import (
    ConfigTask,
    MktStockQuote,
    TradingRuleDefinition,
    TradingSystemRuleBinding,
    WatchPool,
    WatchSignal,
)
from app.services.prd_v1 import SeedService
from app.services.tasks import TaskService


def test_seed_includes_scan_watch_rules_task(db_session):
    SeedService(db_session).init_defaults()

    task = db_session.query(ConfigTask).filter(ConfigTask.task_name == "scan_watch_rules").first()

    assert task is not None
    assert task.owner_module == "signal"
    assert task.task_type == "scheduled"


def test_scan_watch_rules_executes_safe_rule_without_signal(db_session):
    db_session.add(
        TradingRuleDefinition(
            rule_code="test_always_false",
            rule_name="测试永不触发",
            rule_type="filter",
            timeframe="daily",
            executor_key="always_false",
            enabled=True,
        )
    )
    db_session.add(
        TradingSystemRuleBinding(
            system_code="test_system",
            rule_code="test_always_false",
            stage="observe",
            required=True,
            logic_group="test",
            logic_operator="AND",
            enabled=True,
            sort_order=1,
            config_json={},
        )
    )
    db_session.add(
        WatchPool(
            stock_code="000001.SZ",
            stock_name="平安银行",
            active=True,
            status="watching",
            monitor_enabled=True,
            signal_enabled=True,
            system_stage="observe",
            trading_system_code="test_system",
            trading_system="test_system",
            system_params_json={"platform_upper_price": 12.5},
        )
    )
    db_session.commit()

    log = TaskService(db_session).scan_watch_rules(date(2026, 5, 24))

    assert log.run_status == "success"
    assert log.affected_rows == 1
    assert db_session.query(WatchSignal).count() == 0


def test_scan_watch_rules_generates_platform_breakout_buy_signal(db_session):
    SeedService(db_session).init_defaults()
    db_session.add(
        MktStockQuote(
            stock_code="603019.SH",
            stock_name="中科曙光",
            latest_price=25.05,
            change_pct=1.2,
        )
    )
    watch = WatchPool(
        stock_code="603019.SH",
        stock_name="中科曙光",
        active=True,
        status="watching",
        monitor_enabled=True,
        signal_enabled=True,
        system_stage="observe",
        trading_system_code="platform_breakout",
        trading_system="platform_breakout",
        system_params_json={
            "platform_upper_price": 24.0,
            "platform_support_price": 23.0,
            "key_observe_price": 24.5,
            "invalid_condition": "跌破平台支撑",
        },
    )
    db_session.add(watch)
    db_session.commit()

    log = TaskService(db_session).scan_watch_rules(date(2026, 5, 24))
    signals = db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).all()

    assert log.run_status == "success"
    assert len(signals) >= 1
    assert {signal.signal_type for signal in signals} == {"buy"}
    assert {signal.signal_status for signal in signals} == {"buy_pending_confirm"}
    assert all(signal.rule_code in {"b5_divergence", "b15_divergence"} for signal in signals)
    assert all(signal.trading_system_code == "platform_breakout" for signal in signals)
    assert all(signal.notification_sent is False for signal in signals)
    assert all(signal.notification_error for signal in signals)
    assert "email notification is disabled" in (log.error_message or "")
    refreshed = db_session.get(WatchPool, watch.id)
    assert refreshed.status == "buy_pending_confirm"
    assert refreshed.system_stage == "buy_confirm"
    assert refreshed.signal_enabled is False
    assert db_session.get(WatchPool, watch.id).next_action == "等待人工确认买入"

    second = TaskService(db_session).scan_watch_rules(date(2026, 5, 24))
    assert second.run_status == "success"
    assert second.affected_rows == 0
    assert db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).count() == len(signals)


def _add_false_observe_rule(db_session, system_code="filter_system"):
    db_session.add(
        TradingRuleDefinition(
            rule_code=f"{system_code}_always_false",
            rule_name="永不触发",
            rule_type="filter",
            timeframe="daily",
            executor_key="always_false",
            enabled=True,
        )
    )
    db_session.add(
        TradingSystemRuleBinding(
            system_code=system_code,
            rule_code=f"{system_code}_always_false",
            stage="observe",
            required=True,
            logic_group="test",
            logic_operator="AND",
            enabled=True,
            sort_order=1,
            config_json={},
        )
    )


def _add_watch(db_session, **overrides):
    data = {
        "stock_code": "000002.SZ",
        "stock_name": "测试股票",
        "active": True,
        "status": "watching",
        "monitor_enabled": True,
        "signal_enabled": True,
        "system_stage": "observe",
        "trading_system_code": "filter_system",
        "trading_system": "filter_system",
        "system_params_json": {"platform_upper_price": 12.5},
    }
    data.update(overrides)
    watch = WatchPool(**data)
    db_session.add(watch)
    db_session.commit()
    return watch


def test_scan_watch_rules_skips_monitor_disabled_watch(db_session):
    _add_false_observe_rule(db_session)
    _add_watch(db_session, monitor_enabled=False)

    log = TaskService(db_session).scan_watch_rules(date(2026, 5, 24))

    assert log.run_status == "success"
    assert log.affected_rows == 0
    assert db_session.query(WatchSignal).count() == 0


def test_scan_watch_rules_skips_signal_disabled_watch(db_session):
    _add_false_observe_rule(db_session)
    _add_watch(db_session, signal_enabled=False)

    log = TaskService(db_session).scan_watch_rules(date(2026, 5, 24))

    assert log.run_status == "success"
    assert log.affected_rows == 0
    assert db_session.query(WatchSignal).count() == 0


def test_scan_watch_rules_skips_buy_pending_confirm_watch(db_session):
    _add_false_observe_rule(db_session)
    _add_watch(db_session, status="buy_pending_confirm")

    log = TaskService(db_session).scan_watch_rules(date(2026, 5, 24))

    assert log.run_status == "success"
    assert log.affected_rows == 0
    assert db_session.query(WatchSignal).count() == 0


def test_watch_rule_preview_is_dry_run(client, db_session):
    _add_false_observe_rule(db_session)
    watch = _add_watch(db_session)
    before_status = watch.status
    before_stage = watch.system_stage

    response = client.post(f"/api/h5/watch-pool/{watch.id}/rule-preview")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["watch_id"] == watch.id
    assert data["required_passed"] is False
    assert data["buy_signal_triggered"] is False
    assert data["would_generate_signal"] is False
    assert data["rules"][0]["rule_code"] == "filter_system_always_false"
    assert data["rules"][0]["rule_name"] == "永不触发"
    assert data["rules"][0]["triggered"] is False
    assert db_session.query(WatchSignal).count() == 0
    db_session.refresh(watch)
    assert watch.status == before_status
    assert watch.system_stage == before_stage
