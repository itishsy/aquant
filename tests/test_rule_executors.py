from dataclasses import dataclass
from datetime import date, datetime

from app.rule_executors import RuleContext, get_executor, list_executors


@dataclass
class FakeBar:
    kline_time: datetime
    low_price: float
    close_price: float
    high_price: float | None = None
    volume: float | None = None


def test_registry_finds_always_false_executor():
    assert "always_false" in list_executors()
    executor = get_executor("always_false")
    assert executor is not None

    result = executor.execute(
        RuleContext(
            watch_id=1,
            stock_code="000001.SZ",
            stock_name="平安银行",
            trading_system_code="breakout",
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


def test_registry_uses_break_level_instead_of_legacy_break_price():
    assert "break_level" in list_executors()
    assert get_executor("break_level") is not None
    assert "break_price" not in list_executors()
    assert get_executor("break_price") is None


def test_registry_contains_extended_generic_executors():
    for executor_key in ["breakout_level", "near_level", "volume_spike", "ma_trend", "profit_loss_threshold"]:
        assert executor_key in list_executors()
        assert get_executor(executor_key) is not None


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


def _near_ma_context(latest_close=100.0, ma_values=None):
    bars = [
        FakeBar(datetime(2026, 5, 28, 14, 55), low_price=99.0, close_price=100.0),
        FakeBar(datetime(2026, 5, 28, 15, 0), low_price=latest_close - 0.2, close_price=latest_close),
    ]
    return RuleContext(
        watch_id=1,
        stock_code="000001.SZ",
        stock_name="Ping An",
        trading_system_code="uptrend",
        stage="observe",
        rule_config={
            "rule_code": "near_ma20_pullback",
            "rule_name": "Near MA20",
            "rule_type": "filter",
            "timeframe": "daily",
            "config_json": {"signal": {"ma": 20, "near_pct": 0.02, "price_field": "close"}},
        },
        technical={
            "timeframe": "daily",
            "bars": bars,
            "indicators": {"ma": {"ma20": [100.0, 100.0] if ma_values is None else ma_values}},
        },
        trade_date=date(2026, 5, 28),
    )


def test_near_ma_triggers_when_latest_close_is_within_two_percent_of_ma20():
    executor = get_executor("near_ma")

    result = executor.execute(_near_ma_context(latest_close=101.5))

    assert result.triggered is True
    assert result.trigger_price == 101.5
    assert result.snapshot["latest_close"] == 101.5
    assert result.snapshot["latest_ma"] == 100.0
    assert result.snapshot["lower"] == 98.0
    assert result.snapshot["upper"] == 102.0
    assert result.snapshot["executor_key"] == "near_ma"


def test_near_ma_does_not_trigger_when_latest_close_is_too_high():
    executor = get_executor("near_ma")

    result = executor.execute(_near_ma_context(latest_close=103.0))

    assert result.triggered is False
    assert result.trigger_price == 103.0
    assert result.snapshot["latest_ma"] == 100.0


def test_near_ma_does_not_trigger_when_latest_close_is_too_low():
    executor = get_executor("near_ma")

    result = executor.execute(_near_ma_context(latest_close=97.0))

    assert result.triggered is False
    assert result.trigger_price == 97.0
    assert result.snapshot["latest_ma"] == 100.0


def test_near_ma_does_not_trigger_when_ma_data_is_insufficient():
    executor = get_executor("near_ma")

    result = executor.execute(_near_ma_context(latest_close=100.0, ma_values=[100.0, None]))

    assert result.triggered is False
    assert "insufficient" in result.reason
    assert result.snapshot["executor_key"] == "near_ma"


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


def _level_context(executor_key: str, latest_close=10.5, latest_price=None, signal_config=None, system_params=None):
    return RuleContext(
        watch_id=1,
        stock_code="000001.SZ",
        stock_name="Ping An",
        trading_system_code="test_system",
        stage="observe",
        system_params={"key_price": 10.0} if system_params is None else system_params,
        rule_config={
            "rule_code": f"{executor_key}_rule",
            "rule_name": f"{executor_key} rule",
            "rule_type": "buy_signal",
            "latest_close": latest_close,
            "kline_bars": [FakeBar(datetime(2026, 5, 28, 15, 0), low_price=9.8, close_price=latest_close, high_price=10.8)],
            "config_json": {"signal": signal_config or {"target_param": "key_price"}},
        },
        trade_date=date(2026, 5, 28),
        latest_price=latest_price,
    )


def test_breakout_level_close_above_target_triggers():
    result = get_executor("breakout_level").execute(_level_context("breakout_level", latest_close=10.2))

    assert result.triggered is True
    assert result.trigger_price == 10.2
    assert result.snapshot["target"] == 10.0
    assert result.snapshot["price_source"] == "latest_kline_close"


def test_breakout_level_intraday_uses_latest_price():
    result = get_executor("breakout_level").execute(
        _level_context(
            "breakout_level",
            latest_close=9.9,
            latest_price=10.5,
            signal_config={"target_param": "key_price", "breakout_type": "intraday_above", "threshold_pct": 0},
        )
    )

    assert result.triggered is True
    assert result.trigger_price == 10.5
    assert result.snapshot["price_source"] == "latest_price"


def test_near_level_triggers_when_price_is_near_target():
    result = get_executor("near_level").execute(
        _level_context("near_level", latest_close=10.1, signal_config={"target_param": "key_price", "near_pct": 0.02})
    )

    assert result.triggered is True
    assert result.snapshot["lower"] == 9.8
    assert result.snapshot["upper"] == 10.2


def test_near_level_missing_target_does_not_trigger():
    result = get_executor("near_level").execute(
        _level_context("near_level", latest_close=10.1, signal_config={"target_param": "missing"}, system_params={})
    )

    assert result.triggered is False
    assert "Missing near target" in result.reason


def _volume_context(latest_volume=220.0, history_volume=100.0):
    bars = [
        FakeBar(datetime(2026, 5, 28, 14, idx), low_price=9.8, close_price=10.0, high_price=10.2, volume=history_volume)
        for idx in range(3)
    ]
    bars.append(FakeBar(datetime(2026, 5, 28, 15, 0), low_price=10.0, close_price=10.5, high_price=10.8, volume=latest_volume))
    return RuleContext(
        watch_id=1,
        stock_code="000001.SZ",
        stock_name="Ping An",
        trading_system_code="test_system",
        stage="observe",
        rule_config={
            "rule_code": "volume_spike_rule",
            "rule_name": "Volume spike",
            "rule_type": "confirm",
            "config_json": {"signal": {"lookback_bars": 3, "multiplier": 2}},
        },
        technical={"bars": bars, "indicators": {}},
        trade_date=date(2026, 5, 28),
    )


def test_volume_spike_triggers_when_latest_volume_exceeds_average_multiplier():
    result = get_executor("volume_spike").execute(_volume_context())

    assert result.triggered is True
    assert result.snapshot["latest_volume"] == 220.0
    assert result.snapshot["average_volume"] == 100.0


def test_volume_spike_not_triggered_when_volume_is_normal():
    result = get_executor("volume_spike").execute(_volume_context(latest_volume=150.0))

    assert result.triggered is False


def _ma_trend_context(ma5=12.0, ma10=11.0, ma20_values=None, latest_close=12.5, signal_config=None):
    ma20_values = ma20_values or [9.5, 10.0]
    return RuleContext(
        watch_id=1,
        stock_code="000001.SZ",
        stock_name="Ping An",
        trading_system_code="uptrend",
        stage="observe",
        rule_config={
            "rule_code": "ma_trend_rule",
            "rule_name": "MA trend",
            "rule_type": "filter",
            "config_json": {"signal": signal_config or {"mode": "bullish_stack"}},
        },
        technical={
            "bars": [FakeBar(datetime(2026, 5, 28, 15, 0), low_price=12.0, close_price=latest_close, high_price=13.0)],
            "indicators": {"ma": {"ma5": [ma5], "ma10": [ma10], "ma20": ma20_values}},
        },
        trade_date=date(2026, 5, 28),
    )


def test_ma_trend_bullish_stack_triggers():
    result = get_executor("ma_trend").execute(_ma_trend_context())

    assert result.triggered is True
    assert result.snapshot["mode"] == "bullish_stack"


def test_ma_trend_price_above_ma20_triggers():
    result = get_executor("ma_trend").execute(_ma_trend_context(signal_config={"mode": "price_above_ma20"}))

    assert result.triggered is True
    assert "above MA20" in result.reason


def _profit_loss_context(latest_price=11.0, threshold=0.08, mode="profit_ratio_ge"):
    return RuleContext(
        watch_id=1,
        stock_code="000001.SZ",
        stock_name="Ping An",
        trading_system_code="test_system",
        stage="trading",
        rule_config={
            "rule_code": "profit_loss_rule",
            "rule_name": "Profit loss threshold",
            "rule_type": "sell_signal",
            "average_buy_price": 10.0,
            "remaining_amount": 100,
            "config_json": {"signal": {"mode": mode, "threshold": threshold}},
        },
        trade_date=date(2026, 5, 28),
        latest_price=latest_price,
    )


def test_profit_loss_threshold_profit_ratio_triggers():
    result = get_executor("profit_loss_threshold").execute(_profit_loss_context())

    assert result.triggered is True
    assert round(result.snapshot["pnl_ratio"], 4) == 0.1
    assert result.snapshot["pnl_amount"] == 100.0


def test_profit_loss_threshold_loss_ratio_triggers():
    result = get_executor("profit_loss_threshold").execute(_profit_loss_context(latest_price=9.4, threshold=-0.05, mode="loss_ratio_le"))

    assert result.triggered is True
    assert result.signal_level == "S"
