from datetime import date

from app.models import TradingRuleDefinition, TradingSystemRuleBinding, WatchPool, WatchTrade
from app.services.prd_v1 import SeedService
from app.services.rule_data_requirements import RuleDataRequirementService


def _platform_watch(**overrides):
    data = {
        "stock_code": "603019.SH",
        "stock_name": "Test Stock",
        "active": True,
        "status": "watching",
        "system_stage": "observe",
        "monitor_enabled": True,
        "signal_enabled": True,
        "trading_system_code": "breakout",
        "trading_system": "breakout",
    }
    data.update(overrides)
    return WatchPool(**data)


def test_platform_breakout_watch_requirements_include_daily_5m_15m(db_session):
    SeedService(db_session).init_defaults()
    db_session.add(_platform_watch())
    db_session.commit()

    requirements = RuleDataRequirementService(db_session).build_watch_requirements(date(2026, 5, 24))

    stock = requirements["603019.SH"]
    assert set(stock) == {"daily", "5m", "15m"}
    assert stock["daily"]["lookback_bars"] == 5
    assert stock["daily"]["indicators"] == []
    assert stock["daily"]["reasons"] == ["not_break_platform_upper"]
    assert stock["5m"]["lookback_bars"] == 120
    assert stock["5m"]["indicators"] == ["macd"]
    assert stock["5m"]["reasons"] == ["b5_divergence"]
    assert stock["15m"]["lookback_bars"] == 120
    assert stock["15m"]["indicators"] == ["macd"]
    assert stock["15m"]["reasons"] == ["b15_divergence"]


def test_uptrend_watch_requirements_include_daily_ma_5m_15m(db_session):
    SeedService(db_session).init_defaults()
    db_session.add(_platform_watch(trading_system_code="uptrend", trading_system="uptrend"))
    db_session.commit()

    requirements = RuleDataRequirementService(db_session).build_watch_requirements(date(2026, 5, 24))

    stock = requirements["603019.SH"]
    assert set(stock) == {"daily", "5m", "15m"}
    assert stock["daily"]["lookback_bars"] == 60
    assert stock["daily"]["indicators"] == ["ma"]
    assert stock["daily"]["reasons"] == ["near_ma20_pullback"]
    assert stock["5m"]["lookback_bars"] == 120
    assert stock["5m"]["indicators"] == ["macd"]
    assert stock["5m"]["reasons"] == ["b5_divergence"]
    assert stock["15m"]["lookback_bars"] == 120
    assert stock["15m"]["indicators"] == ["macd"]
    assert stock["15m"]["reasons"] == ["b15_divergence"]


def test_platform_breakout_trade_requirements_include_daily_5m_30m(db_session):
    SeedService(db_session).init_defaults()
    db_session.add(
        WatchTrade(
            stock_code="603019.SH",
            stock_name="Test Stock",
            trade_status="open",
            current_stage="trading",
            trading_system_code="breakout",
            trading_system="breakout",
            active_sell_rule_codes_json=["m5_top_divergence", "m30_dead_cross"],
            active_stop_rule_codes_json=["break_platform_support"],
        )
    )
    db_session.commit()

    requirements = RuleDataRequirementService(db_session).build_trade_requirements(date(2026, 5, 24))

    stock = requirements["603019.SH"]
    assert set(stock) == {"daily", "5m", "30m"}
    assert stock["daily"]["lookback_bars"] == 5
    assert stock["daily"]["reasons"] == ["break_platform_support"]
    assert stock["5m"]["lookback_bars"] == 120
    assert stock["5m"]["indicators"] == ["macd"]
    assert stock["5m"]["reasons"] == ["m5_top_divergence"]
    assert stock["30m"]["lookback_bars"] == 120
    assert stock["30m"]["indicators"] == ["macd"]
    assert stock["30m"]["reasons"] == ["m30_dead_cross"]


def test_watch_requirements_skip_monitor_disabled_watch(db_session):
    SeedService(db_session).init_defaults()
    db_session.add(_platform_watch(monitor_enabled=False))
    db_session.commit()

    requirements = RuleDataRequirementService(db_session).build_watch_requirements(date(2026, 5, 24))

    assert requirements == {}


def test_watch_requirements_merge_duplicate_timeframe_requirements(db_session):
    SeedService(db_session).init_defaults()
    db_session.add(
        TradingRuleDefinition(
            rule_code="custom_5m_confirm",
            rule_name="Custom 5m Confirm",
            rule_type="confirm",
            timeframe="5m",
            executor_key="macd_bottom_divergence",
            enabled=True,
        )
    )
    db_session.add(
        TradingSystemRuleBinding(
            system_code="breakout",
            rule_code="custom_5m_confirm",
            stage="observe",
            required=False,
            logic_group="bottom_divergence",
            logic_operator="OR",
            enabled=True,
            sort_order=9,
            config_json={"data": {"timeframe": "5m", "lookback_bars": 150, "indicators": ["ma", "macd"]}},
        )
    )
    db_session.add(_platform_watch())
    db_session.commit()

    requirements = RuleDataRequirementService(db_session).build_watch_requirements(date(2026, 5, 24))

    five_minute = requirements["603019.SH"]["5m"]
    assert five_minute["lookback_bars"] == 150
    assert five_minute["indicators"] == ["macd", "ma"]
    assert five_minute["reasons"] == ["b5_divergence", "custom_5m_confirm"]


def test_seeded_example_ma_binding_can_drive_daily_ma_requirement(db_session):
    SeedService(db_session).init_defaults()
    binding = db_session.query(TradingSystemRuleBinding).filter_by(
        system_code="breakout",
        rule_code="observe_break_ma5",
        stage="observe",
    ).first()
    binding.enabled = True
    db_session.add(_platform_watch())
    db_session.commit()

    requirements = RuleDataRequirementService(db_session).build_watch_requirements(date(2026, 5, 24))

    daily = requirements["603019.SH"]["daily"]
    assert daily["lookback_bars"] == 30
    assert daily["indicators"] == ["ma"]
    assert daily["reasons"] == ["not_break_platform_upper", "observe_break_ma5"]


def test_extended_executor_default_data_requirements(db_session):
    service = RuleDataRequirementService(db_session)
    binding = TradingSystemRuleBinding(system_code="test", rule_code="rule", stage="observe", config_json={})

    cases = {
        "breakout_level": ("daily", 5, []),
        "near_level": ("daily", 5, []),
        "volume_spike": ("daily", 21, []),
        "ma_trend": ("daily", 60, ["ma"]),
        "profit_loss_threshold": ("daily", 1, []),
    }
    for executor_key, expected in cases.items():
        rule = TradingRuleDefinition(rule_code=f"{executor_key}_rule", timeframe="daily", executor_key=executor_key)
        requirement = service.rule_requirement(binding, rule)
        assert (requirement["timeframe"], requirement["lookback_bars"], requirement["indicators"]) == expected
