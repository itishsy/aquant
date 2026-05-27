from dataclasses import dataclass
from datetime import date, datetime

from app.rule_executors import RuleContext, get_executor, list_executors


@dataclass
class FakeBar:
    kline_time: datetime
    low_price: float
    close_price: float
    high_price: float | None = None


def test_registry_finds_always_false_executor():
    assert "always_false" in list_executors()
    executor = get_executor("always_false")
    assert executor is not None

    result = executor.execute(
        RuleContext(
            watch_id=1,
            stock_code="000001.SZ",
            stock_name="平安银行",
            trading_system_code="platform_breakout",
            stage="observe",
            system_params={"platform_upper_price": 12.5},
            rule_config={
                "rule_code": "test_rule",
                "rule_name": "测试规则",
                "rule_type": "filter",
            },
            trade_date=date(2026, 5, 23),
            latest_price=12.3,
        )
    )

    assert result.triggered is False
    assert result.rule_code == "test_rule"
    assert result.rule_name == "测试规则"
    assert result.rule_type == "filter"
    assert result.trigger_price == 12.3
    assert result.snapshot["executor_key"] == "always_false"


def _break_level_context(**overrides):
    data = {
        "watch_id": 1,
        "stock_code": "000001.SZ",
        "stock_name": "Ping An",
        "trading_system_code": "test_system",
        "stage": "observe",
        "system_params": {"key_observe_price": 10.0},
        "rule_config": {
            "rule_code": "break_key_observe",
            "rule_name": "Break key observe price",
            "rule_type": "stop_loss",
            "latest_close": 9.8,
            "latest_time": datetime(2026, 5, 28, 15, 0),
            "kline_bars": [FakeBar(datetime(2026, 5, 28, 15, 0), low_price=9.7, close_price=9.8)],
            "config_json": {
                "signal": {
                    "target_param": "key_observe_price",
                    "break_type": "close_below",
                    "threshold_pct": 0,
                }
            },
        },
        "trade_date": date(2026, 5, 28),
        "latest_price": None,
    }
    data.update(overrides)
    return RuleContext(**data)


def test_break_level_close_below_target_param_triggers():
    executor = get_executor("break_level")

    result = executor.execute(_break_level_context())

    assert result.triggered is True
    assert result.trigger_price == 9.8
    assert result.snapshot["target"] == 10.0
    assert result.snapshot["target_source"] == "system_params.key_observe_price"
    assert result.snapshot["price_source"] == "latest_kline_close"
    assert "broke below target" in result.reason


def test_break_level_not_broken_does_not_trigger():
    executor = get_executor("break_level")
    context = _break_level_context(rule_config={**_break_level_context().rule_config, "latest_close": 10.01})

    result = executor.execute(context)

    assert result.triggered is False
    assert result.trigger_price == 10.01
    assert "has not broken below target" in result.reason


def test_break_level_missing_target_param_does_not_trigger_with_clear_reason():
    executor = get_executor("break_level")
    context = _break_level_context(
        system_params={},
        rule_config={
            **_break_level_context().rule_config,
            "config_json": {"signal": {"target_param": "missing_price", "break_type": "close_below"}},
        },
    )

    result = executor.execute(context)

    assert result.triggered is False
    assert result.trigger_price is None
    assert "Missing break target" in result.reason
    assert result.snapshot["target_param"] == "missing_price"


def test_break_level_intraday_below_uses_latest_price():
    executor = get_executor("break_level")
    context = _break_level_context(
        latest_price=9.5,
        rule_config={
            **_break_level_context().rule_config,
            "latest_close": 10.5,
            "config_json": {
                "signal": {
                    "target_param": "key_observe_price",
                    "break_type": "intraday_below",
                    "threshold_pct": 0,
                }
            },
        },
    )

    result = executor.execute(context)

    assert result.triggered is True
    assert result.trigger_price == 9.5
    assert result.snapshot["price_source"] == "latest_price"


def _break_ma_context(closes, ma_values, signal_config=None):
    bars = [
        FakeBar(datetime(2026, 5, 28, 14, 55), low_price=closes[-2] - 0.1, close_price=closes[-2]),
        FakeBar(datetime(2026, 5, 28, 15, 0), low_price=closes[-1] - 0.1, close_price=closes[-1]),
    ]
    return RuleContext(
        watch_id=1,
        stock_code="000001.SZ",
        stock_name="Ping An",
        trading_system_code="test_system",
        stage="trading",
        rule_config={
            "rule_code": "break_ma_rule",
            "rule_name": "Break MA rule",
            "rule_type": "stop_loss",
            "config_json": {"signal": signal_config or {"ma": 5, "break_type": "cross_down"}},
        },
        technical={
            "bars": bars,
            "indicators": {"ma": {"ma5": ma_values, "ma10": ma_values, "ma20": ma_values}},
        },
        trade_date=date(2026, 5, 28),
    )


def test_break_ma_cross_down_ma5_triggers():
    executor = get_executor("break_ma")

    result = executor.execute(_break_ma_context([10.2, 9.8], [10.0, 10.0]))

    assert result.triggered is True
    assert result.trigger_price == 9.8
    assert result.trigger_time == datetime(2026, 5, 28, 15, 0)
    assert result.snapshot["ma"] == 5
    assert result.snapshot["break_type"] == "cross_down"


def test_break_ma_cross_down_not_triggered_when_already_below():
    executor = get_executor("break_ma")

    result = executor.execute(_break_ma_context([9.8, 9.7], [10.0, 10.0]))

    assert result.triggered is False
    assert result.trigger_price == 9.7
    assert "has not broken MA5" in result.reason


def test_break_ma_below_mode_triggers_when_latest_close_below_ma5():
    executor = get_executor("break_ma")

    result = executor.execute(_break_ma_context([9.8, 9.7], [10.0, 10.0], {"ma": 5, "break_type": "below"}))

    assert result.triggered is True
    assert result.snapshot["break_type"] == "below"


def test_break_ma_supports_ma10_and_ma20_config():
    executor = get_executor("break_ma")

    ma10 = executor.execute(_break_ma_context([10.2, 9.8], [10.0, 10.0], {"ma": 10, "break_type": "cross_down"}))
    ma20 = executor.execute(_break_ma_context([20.2, 19.8], [20.0, 20.0], {"ma": 20, "break_type": "cross_down"}))

    assert ma10.triggered is True
    assert ma10.snapshot["ma"] == 10
    assert ma20.triggered is True
    assert ma20.snapshot["ma"] == 20


def _pullback_context(latest_close=96.9, signal_config=None, system_params=None):
    bars = [
        FakeBar(datetime(2026, 5, 28, 14, 45), low_price=98.0, close_price=99.0, high_price=100.0),
        FakeBar(datetime(2026, 5, 28, 14, 50), low_price=97.0, close_price=98.5, high_price=101.0),
        FakeBar(datetime(2026, 5, 28, 15, 0), low_price=latest_close - 0.2, close_price=latest_close, high_price=98.0),
    ]
    return RuleContext(
        watch_id=1,
        stock_code="000001.SZ",
        stock_name="Ping An",
        trading_system_code="test_system",
        stage="observe",
        system_params={"platform_upper_price": 100.0} if system_params is None else system_params,
        rule_config={
            "rule_code": "pullback_rule",
            "rule_name": "Pullback rule",
            "rule_type": "filter",
            "config_json": {"signal": signal_config or {"mode": "from_recent_high", "pullback_pct": 0.03}},
        },
        technical={"bars": bars, "indicators": {}},
        trade_date=date(2026, 5, 28),
    )


def test_pullback_from_recent_high_triggers_after_three_percent_drop():
    executor = get_executor("pullback_to_level")

    result = executor.execute(_pullback_context(latest_close=97.0))

    assert result.triggered is True
    assert result.trigger_price == 97.0
    assert result.snapshot["mode"] == "from_recent_high"
    assert result.snapshot["recent_high"] == 101.0
    assert result.snapshot["threshold"] == 97.97


def test_pullback_from_recent_high_not_triggered_before_threshold():
    executor = get_executor("pullback_to_level")

    result = executor.execute(_pullback_context(latest_close=98.0))

    assert result.triggered is False
    assert result.trigger_price == 98.0
    assert "has not pulled back" in result.reason


def test_pullback_near_platform_upper_price_triggers():
    executor = get_executor("pullback_to_level")
    context = _pullback_context(
        latest_close=100.5,
        signal_config={"mode": "near_param_level", "target_param": "platform_upper_price", "near_pct": 0.01},
        system_params={"platform_upper_price": 100.0},
    )

    result = executor.execute(context)

    assert result.triggered is True
    assert result.snapshot["mode"] == "near_param_level"
    assert result.snapshot["target"] == 100.0
    assert result.snapshot["threshold"] == {"lower": 99.0, "upper": 101.0}


def test_pullback_near_param_level_missing_target_does_not_trigger():
    executor = get_executor("pullback_to_level")
    context = _pullback_context(
        latest_close=100.5,
        signal_config={"mode": "near_param_level", "target_param": "platform_upper_price", "near_pct": 0.01},
        system_params={},
    )

    result = executor.execute(context)

    assert result.triggered is False
    assert "Missing target_param" in result.reason
    assert result.snapshot["target"] is None
