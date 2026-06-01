from datetime import date, datetime, timedelta

from app.models import (
    ConfigTask,
    MktStockQuote,
    TradingRuleDefinition,
    TradingSystemRuleBinding,
    WatchPool,
    WatchSignal,
)
from app.services.prd_v1 import SeedService
from app.services.kline_repository import KlineRepository
from app.services.tasks import TaskService


def _seed_daily_bars(db_session, stock_code="603019.SH", close_price=25.05, count=5):
    repo = KlineRepository(db_session)
    start = date(2026, 5, 20)
    repo.upsert_rows(
        stock_code,
        "daily",
        [
            {
                "trade_date": start + timedelta(days=idx),
                "open": close_price - 0.2,
                "high": close_price + 0.2,
                "low": close_price - 0.5,
                "close": close_price,
                "volume": 100000 + idx,
            }
            for idx in range(count)
        ],
        "test",
    )


def _seed_divergence_bars(db_session, stock_code="603019.SH", timeframe="5m"):
    closes = [25.8, 25.4, 25.0, 24.8, 24.6, 24.55, 24.62, 24.74, 24.88, 25.05]
    start = datetime(2026, 5, 24, 9, 35)
    KlineRepository(db_session).upsert_rows(
        stock_code,
        timeframe,
        [
            {
                "kline_time": start + timedelta(minutes=5 * idx),
                "open": close - 0.08,
                "high": close + 0.12,
                "low": close - 0.15,
                "close": close,
                "volume": 10000 - idx * 350,
            }
            for idx, close in enumerate(closes)
        ],
        "test",
    )


def _seed_daily_ma_bars(db_session, stock_code="603019.SH", latest_close=100.0, base_close=100.0, count=60, end_date=None):
    repo = KlineRepository(db_session)
    end_date = end_date or date(2026, 5, 24)
    start = end_date - timedelta(days=count - 1)
    rows = []
    for idx in range(count):
        close = latest_close if idx == count - 1 else base_close
        rows.append(
            {
                "trade_date": start + timedelta(days=idx),
                "open": close - 0.2,
                "high": close + 0.2,
                "low": close - 0.5,
                "close": close,
                "volume": 100000 + idx,
            }
        )
    repo.upsert_rows(stock_code, "daily", rows, "test")


def _seed_intraday_bars(db_session, stock_code="603019.SH", timeframe="5m", divergent=True, count=120):
    minutes = 15 if timeframe == "15m" else 5
    end = datetime(2026, 5, 24, 10, 15 if timeframe == "15m" else 20)
    start = end - timedelta(minutes=minutes * (count - 1))
    if divergent:
        tail = [25.8, 25.4, 25.0, 24.8, 24.6, 24.55, 24.62, 24.74, 24.88, 25.05]
    else:
        tail = [25.0 for _idx in range(10)]
    prefix_count = count - len(tail)
    closes = [tail[0] for _idx in range(prefix_count)] + tail
    KlineRepository(db_session).upsert_rows(
        stock_code,
        timeframe,
        [
            {
                "kline_time": start + timedelta(minutes=minutes * idx),
                "open": close - 0.08,
                "high": close + 0.12,
                "low": close - 0.15,
                "close": close,
                "volume": 10000 - (idx % 20) * 100,
            }
            for idx, close in enumerate(closes)
        ],
        "test",
    )


def _add_uptrend_watch(db_session, stock_code="603019.SH"):
    return _add_watch(
        db_session,
        stock_code=stock_code,
        stock_name="Uptrend Stock",
        trading_system_code="uptrend",
        trading_system="uptrend",
        system_params_json={},
    )


def _scan_uptrend(db_session, now=None):
    return TaskService(db_session, now=now or datetime(2026, 5, 24, 10, 21)).scan_watch_rules(date(2026, 5, 24))


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

    log = TaskService(db_session, now=datetime(2026, 5, 24, 10, 21)).scan_watch_rules(date(2026, 5, 24))

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
            source_update_time=datetime(2026, 5, 24, 10, 20),
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
        trading_system_code="breakout",
        trading_system="breakout",
        system_params_json={
            "platform_upper_price": 24.0,
            "platform_support_price": 23.0,
            "key_observe_price": 24.5,
            "invalid_condition": "跌破平台支撑",
        },
    )
    db_session.add(watch)
    for rule_code in ["b5_divergence", "b15_divergence"]:
        binding = db_session.query(TradingSystemRuleBinding).filter_by(
            system_code="breakout",
            rule_code=rule_code,
            stage="observe",
        ).first()
        binding.config_json = {"data": {"timeframe": "5m" if rule_code == "b5_divergence" else "15m", "lookback_bars": 10, "indicators": ["macd"]}}
    db_session.commit()
    _seed_daily_bars(db_session)
    _seed_divergence_bars(db_session, timeframe="5m")
    _seed_divergence_bars(db_session, timeframe="15m")

    log = TaskService(db_session, now=datetime(2026, 5, 24, 10, 21)).scan_watch_rules(date(2026, 5, 24))
    signals = db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).all()

    assert log.run_status == "success"
    assert len(signals) >= 1
    assert {signal.signal_type for signal in signals} == {"buy"}
    assert {signal.signal_status for signal in signals} == {"buy_pending_confirm"}
    assert all(signal.rule_code in {"b5_divergence", "b15_divergence"} for signal in signals)
    assert all(signal.trading_system_code == "breakout" for signal in signals)
    for signal in signals:
        snapshot = signal.snapshot_json
        assert snapshot["data_status"] == "ok"
        assert snapshot["timeframe"] in {"5m", "15m"}
        assert snapshot["latest_kline_time"] is not None
        assert snapshot["expected_latest_time"] is not None
        assert snapshot["bar_count"] == 10
        assert snapshot["required_bars"] == 10
        assert snapshot["executor_key"] == "macd_bottom_divergence"
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


def test_scan_watch_rules_does_not_call_provider_and_reports_missing_data(db_session, monkeypatch):
    SeedService(db_session).init_defaults()
    db_session.add(
        WatchPool(
            stock_code="603019.SH",
            stock_name="中科曙光",
            active=True,
            status="watching",
            monitor_enabled=True,
            signal_enabled=True,
            system_stage="observe",
            trading_system_code="breakout",
            trading_system="breakout",
            system_params_json={"platform_upper_price": 24.0},
        )
    )
    db_session.commit()

    def _raise_provider():
        raise AssertionError("provider must not be called during scan_watch_rules")

    monkeypatch.setattr("app.services.tasks.ProviderFactory.create", _raise_provider)
    log = TaskService(db_session).scan_watch_rules(date(2026, 5, 24))

    assert log.run_status == "success"
    assert db_session.query(WatchSignal).count() == 0
    assert "No kline data" in (log.error_message or "")


def _add_not_break_filter_system(db_session, system_code="quote_system"):
    db_session.add(
        TradingRuleDefinition(
            rule_code=f"{system_code}_not_break",
            rule_name="Not break price",
            rule_type="filter",
            timeframe="daily",
            executor_key="not_break_price",
            enabled=True,
        )
    )
    db_session.add(
        TradingSystemRuleBinding(
            system_code=system_code,
            rule_code=f"{system_code}_not_break",
            stage="observe",
            required=True,
            logic_group="quote",
            logic_operator="AND",
            enabled=True,
            sort_order=1,
            config_json={"data": {"timeframe": "daily", "lookback_bars": 5, "indicators": []}},
        )
    )


def test_scan_watch_rules_skips_not_break_price_when_quote_is_stale(db_session):
    _add_not_break_filter_system(db_session)
    db_session.add(
        MktStockQuote(
            stock_code="000003.SZ",
            stock_name="娴嬭瘯鑲＄エ",
            latest_price=25.0,
            source_update_time=datetime(2026, 5, 24, 10, 0),
        )
    )
    _add_watch(
        db_session,
        stock_code="000003.SZ",
        trading_system_code="quote_system",
        trading_system="quote_system",
        system_params_json={"platform_upper_price": 24.0},
    )
    _seed_daily_bars(db_session, stock_code="000003.SZ", close_price=25.0)

    log = TaskService(db_session, now=datetime(2026, 5, 24, 10, 21)).scan_watch_rules(date(2026, 5, 24))

    assert log.run_status == "success"
    assert log.affected_rows == 1
    assert db_session.query(WatchSignal).count() == 0
    assert "Quote stale" in (log.error_message or "")


def test_scan_watch_rules_executes_not_break_price_when_quote_is_fresh(db_session):
    _add_not_break_filter_system(db_session, system_code="fresh_quote_system")
    db_session.add(
        MktStockQuote(
            stock_code="000004.SZ",
            stock_name="娴嬭瘯鑲＄エ",
            latest_price=25.0,
            source_update_time=datetime(2026, 5, 24, 10, 15),
        )
    )
    _add_watch(
        db_session,
        stock_code="000004.SZ",
        trading_system_code="fresh_quote_system",
        trading_system="fresh_quote_system",
        system_params_json={"platform_upper_price": 24.0},
    )
    _seed_daily_bars(db_session, stock_code="000004.SZ", close_price=25.0)

    log = TaskService(db_session, now=datetime(2026, 5, 24, 10, 21)).scan_watch_rules(date(2026, 5, 24))

    assert log.run_status == "success"
    assert log.affected_rows == 1
    assert db_session.query(WatchSignal).count() == 0
    assert "Quote stale" not in (log.error_message or "")


def test_scan_watch_rules_does_not_generate_signal_when_kline_is_stale(db_session):
    SeedService(db_session).init_defaults()
    db_session.add(
        MktStockQuote(
            stock_code="603019.SH",
            stock_name="涓鏇欏厜",
            latest_price=25.05,
            change_pct=1.2,
            source_update_time=datetime(2026, 5, 24, 14, 45),
        )
    )
    watch = WatchPool(
        stock_code="603019.SH",
        stock_name="涓鏇欏厜",
        active=True,
        status="watching",
        monitor_enabled=True,
        signal_enabled=True,
        system_stage="observe",
        trading_system_code="breakout",
        trading_system="breakout",
        system_params_json={
            "platform_upper_price": 24.0,
            "platform_support_price": 23.0,
            "key_observe_price": 24.5,
            "invalid_condition": "璺岀牬骞冲彴鏀拺",
        },
    )
    db_session.add(watch)
    for rule_code in ["b5_divergence", "b15_divergence"]:
        binding = db_session.query(TradingSystemRuleBinding).filter_by(
            system_code="breakout",
            rule_code=rule_code,
            stage="observe",
        ).first()
        binding.config_json = {
            "data": {
                "timeframe": "5m" if rule_code == "b5_divergence" else "15m",
                "lookback_bars": 10,
                "indicators": ["macd"],
            }
        }
    db_session.commit()
    _seed_daily_bars(db_session)
    _seed_divergence_bars(db_session, timeframe="5m")
    _seed_divergence_bars(db_session, timeframe="15m")

    log = TaskService(db_session, now=datetime(2026, 5, 24, 14, 46)).scan_watch_rules(date(2026, 5, 24))

    assert log.run_status == "success"
    assert db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).count() == 0
    assert "older than expected" in (log.error_message or "")


def test_uptrend_near_ma20_without_bottom_divergence_does_not_generate_buy_signal(db_session):
    SeedService(db_session).init_defaults()
    watch = _add_uptrend_watch(db_session)
    _seed_daily_ma_bars(db_session, latest_close=100.0, base_close=100.0)
    _seed_intraday_bars(db_session, timeframe="5m", divergent=False)
    _seed_intraday_bars(db_session, timeframe="15m", divergent=False)

    log = _scan_uptrend(db_session)

    assert log.run_status == "success"
    assert db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).count() == 0
    db_session.refresh(watch)
    assert watch.status == "watching"
    assert watch.system_stage == "observe"


def test_uptrend_bottom_divergence_without_near_ma20_does_not_generate_buy_signal(db_session):
    SeedService(db_session).init_defaults()
    watch = _add_uptrend_watch(db_session)
    _seed_daily_ma_bars(db_session, latest_close=110.0, base_close=100.0)
    _seed_intraday_bars(db_session, timeframe="5m", divergent=True)
    _seed_intraday_bars(db_session, timeframe="15m", divergent=False)

    log = _scan_uptrend(db_session)

    assert log.run_status == "success"
    assert db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).count() == 0
    db_session.refresh(watch)
    assert watch.status == "watching"
    assert watch.system_stage == "observe"


def test_uptrend_near_ma20_with_5m_bottom_divergence_generates_buy_signal_when_email_disabled(db_session):
    SeedService(db_session).init_defaults()
    watch = _add_uptrend_watch(db_session)
    _seed_daily_ma_bars(db_session, latest_close=100.0, base_close=100.0)
    _seed_intraday_bars(db_session, timeframe="5m", divergent=True)
    _seed_intraday_bars(db_session, timeframe="15m", divergent=False)

    log = _scan_uptrend(db_session)
    signals = db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).all()

    assert log.run_status == "success"
    assert len(signals) == 1
    signal = signals[0]
    assert signal.rule_code == "b5_divergence"
    assert signal.signal_type == "buy"
    assert signal.signal_status == "buy_pending_confirm"
    assert signal.trading_system_code == "uptrend"
    assert signal.notification_sent is False
    assert "email notification is disabled" in signal.notification_error
    assert "email notification is disabled" in (log.error_message or "")
    db_session.refresh(watch)
    assert watch.status == "buy_pending_confirm"
    assert watch.system_stage == "buy_confirm"
    assert watch.signal_enabled is False


def test_uptrend_near_ma20_with_15m_bottom_divergence_generates_buy_signal(db_session):
    SeedService(db_session).init_defaults()
    watch = _add_uptrend_watch(db_session)
    _seed_daily_ma_bars(db_session, latest_close=100.0, base_close=100.0)
    _seed_intraday_bars(db_session, timeframe="5m", divergent=False)
    _seed_intraday_bars(db_session, timeframe="15m", divergent=True)

    log = _scan_uptrend(db_session)
    signals = db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).all()

    assert log.run_status == "success"
    assert len(signals) == 1
    assert signals[0].rule_code == "b15_divergence"
    assert signals[0].trading_system_code == "uptrend"


def test_uptrend_does_not_generate_signal_when_required_ma_data_is_insufficient(db_session):
    SeedService(db_session).init_defaults()
    watch = _add_uptrend_watch(db_session)
    _seed_daily_ma_bars(db_session, latest_close=100.0, base_close=100.0, count=20)
    _seed_intraday_bars(db_session, timeframe="5m", divergent=True)

    log = _scan_uptrend(db_session)

    assert log.run_status == "success"
    assert db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).count() == 0
    assert "Need 60 bars" in (log.error_message or "")


def test_uptrend_does_not_generate_signal_when_required_ma_data_is_stale(db_session):
    SeedService(db_session).init_defaults()
    watch = _add_uptrend_watch(db_session)
    _seed_daily_ma_bars(db_session, latest_close=100.0, base_close=100.0, count=60, end_date=date(2026, 5, 23))
    _seed_intraday_bars(db_session, timeframe="5m", divergent=True)
    _seed_intraday_bars(db_session, timeframe="15m", divergent=True)

    log = _scan_uptrend(db_session, now=datetime(2026, 5, 24, 15, 10))

    assert log.run_status == "success"
    assert db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).count() == 0
    assert "older than expected" in (log.error_message or "")


def _add_break_level_observe_rule(db_session, system_code: str, rule_type: str, rule_code: str):
    db_session.add(
        TradingRuleDefinition(
            rule_code=rule_code,
            rule_name=f"{rule_type} rule",
            rule_type=rule_type,
            timeframe="daily",
            executor_key="break_level",
            enabled=True,
        )
    )
    db_session.add(
        TradingSystemRuleBinding(
            system_code=system_code,
            rule_code=rule_code,
            stage="observe",
            required=False,
            logic_group="observe_alert",
            logic_operator="OR",
            enabled=True,
            sort_order=1,
            config_json={
                "data": {"timeframe": "daily", "lookback_bars": 5, "indicators": []},
                "signal": {"target_value": 24.0, "break_type": "close_below", "threshold_pct": 0},
            },
        )
    )


def test_scan_watch_rules_generates_observe_risk_signal(db_session):
    _add_break_level_observe_rule(db_session, "observe_risk_system", "observe_risk", "observe_risk_break")
    watch = _add_watch(
        db_session,
        stock_code="000005.SZ",
        trading_system_code="observe_risk_system",
        trading_system="observe_risk_system",
    )
    _seed_daily_bars(db_session, stock_code="000005.SZ", close_price=23.5)

    log = TaskService(db_session, now=datetime(2026, 5, 24, 15, 10)).scan_watch_rules(date(2026, 5, 24))
    signal = db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).first()

    assert log.run_status == "success"
    assert signal is not None
    assert signal.signal_type == "risk"
    assert signal.rule_type == "observe_risk"
    assert signal.signal_status == "observe_risk_pending"
    assert signal.snapshot_json["data_status"] == "ok"
    assert signal.snapshot_json["timeframe"] == "daily"
    assert signal.snapshot_json["latest_kline_time"] == datetime(2026, 5, 24).isoformat()
    assert signal.snapshot_json["expected_latest_time"] == datetime(2026, 5, 24).isoformat()
    assert signal.snapshot_json["bar_count"] == 5
    assert signal.snapshot_json["required_bars"] == 5
    assert signal.snapshot_json["executor_key"] == "break_level"
    refreshed = db_session.get(WatchPool, watch.id)
    assert refreshed.system_stage == "observe"
    assert refreshed.status == "watching"
    assert refreshed.next_action == "出现观察风险，请人工确认是否继续观察"


def test_scan_watch_rules_generates_invalid_signal_without_buy_confirm_and_deduplicates(db_session):
    _add_break_level_observe_rule(db_session, "observe_invalid_system", "invalid_signal", "observe_invalid_break")
    watch = _add_watch(
        db_session,
        stock_code="000006.SZ",
        trading_system_code="observe_invalid_system",
        trading_system="observe_invalid_system",
    )
    _seed_daily_bars(db_session, stock_code="000006.SZ", close_price=23.5)

    first = TaskService(db_session, now=datetime(2026, 5, 24, 15, 10)).scan_watch_rules(date(2026, 5, 24))
    second = TaskService(db_session, now=datetime(2026, 5, 24, 15, 10)).scan_watch_rules(date(2026, 5, 24))
    signals = db_session.query(WatchSignal).filter(WatchSignal.watch_id == watch.id).all()

    assert first.run_status == "success"
    assert second.run_status == "success"
    assert len(signals) == 1
    assert signals[0].signal_type == "risk"
    assert signals[0].rule_type == "invalid_signal"
    assert signals[0].signal_status == "observe_invalid_pending"
    refreshed = db_session.get(WatchPool, watch.id)
    assert refreshed.system_stage == "observe"
    assert refreshed.status == "watching"


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
