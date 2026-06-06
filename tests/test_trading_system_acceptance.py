from app.models import (
    ConfigTask,
    TradingRuleDefinition,
    TradingSystemDefinition,
    TradingSystemParamDefinition,
    TradingSystemRuleBinding,
    WatchPool,
    WatchSignal,
)
from app.services.prd_v1 import SeedService
from app.tasks.scheduler import build_scheduler


def test_trading_system_seed_data_is_ready_for_platform_breakout(db_session):
    SeedService(db_session).init_defaults()

    system_codes = {
        row.system_code
        for row in db_session.query(TradingSystemDefinition).filter(TradingSystemDefinition.enabled.is_(True)).all()
    }
    assert {"breakout", "uptrend", "relay", "rebound"} <= system_codes

    required_params = {
        row.param_key
        for row in db_session.query(TradingSystemParamDefinition)
        .filter(
            TradingSystemParamDefinition.system_code == "breakout",
            TradingSystemParamDefinition.required.is_(True),
        )
        .all()
    }
    assert {"platform_support_price", "key_observe_price"} <= required_params

    stage_rules = {
        (row.stage, row.rule_code)
        for row in db_session.query(TradingSystemRuleBinding)
        .filter(
            TradingSystemRuleBinding.system_code == "breakout",
            TradingSystemRuleBinding.enabled.is_(True),
        )
        .all()
    }
    assert {
        ("observe", "b5_divergence"),
        ("observe", "b15_divergence"),
        ("trading", "m5_top_divergence"),
        ("trading", "m30_dead_cross"),
        ("stop_loss", "break_platform_support"),
    } <= stage_rules

    task_names = {row.task_name for row in db_session.query(ConfigTask).all()}
    assert {"scan_watch_rules", "scan_watch_remove_rules", "scan_trade_rules"} <= task_names


def test_scheduler_registers_trading_system_rule_jobs():
    scheduler = build_scheduler()

    job_ids = {job.id for job in scheduler.get_jobs()}

    assert {
        "collect_all_market",
        "update_watch_prices",
        "scan_watch_signals",
        "auto_remove_watch_pool",
        "prepare_watch_kline_data",
        "scan_watch_rules",
        "scan_watch_remove_rules",
        "scan_trade_rules",
    } <= job_ids
    assert scheduler.get_job("prepare_watch_kline_data").trigger.interval.total_seconds() == 900
    assert scheduler.get_job("scan_watch_rules").trigger.interval.total_seconds() == 900
    assert scheduler.get_job("scan_trade_rules").trigger.interval.total_seconds() == 600
    assert "hour='20'" in str(scheduler.get_job("scan_watch_remove_rules").trigger)
    assert "minute='0'" in str(scheduler.get_job("scan_watch_remove_rules").trigger)


def test_watch_rule_preview_requires_trading_system_code(client, db_session):
    watch = WatchPool(
        stock_code="000001.SZ",
        stock_name="Ping An Bank",
        active=True,
        status="watching",
        monitor_enabled=True,
        signal_enabled=True,
        system_stage="observe",
    )
    db_session.add(watch)
    db_session.commit()

    response = client.post(f"/api/h5/watch-pool/{watch.id}/rule-preview")

    assert response.status_code == 400
    assert "trading_system_code" in response.json()["detail"]
    assert db_session.query(WatchSignal).count() == 0
    db_session.refresh(watch)
    assert watch.status == "watching"
    assert watch.system_stage == "observe"
    assert watch.signal_enabled is True


def test_add_watch_with_trading_system_accepts_current_required_params(client, db_session):
    SeedService(db_session).init_defaults()

    response = client.post(
        "/api/h5/watch-pool",
        json={
            "stock_code": "000001.SZ",
            "stock_name": "Ping An Bank",
            "entry_reason": "acceptance test",
            "trading_system_code": "breakout",
            "system_params_json": {
                "platform_upper_price": 12.5,
                "platform_support_price": 11.8,
                "key_observe_price": 12.6,
            },
        },
    )

    assert response.status_code == 200
    assert db_session.query(WatchPool).count() == 1


def test_uptrend_new_rules_created_by_seed(db_session):
    SeedService(db_session).init_defaults()

    rules = {
        row.rule_code: row
        for row in db_session.query(TradingRuleDefinition)
        .filter(TradingRuleDefinition.rule_code.in_([
            "uptrend_not_break_ma20",
            "uptrend_break_ma20_consecutive_remove",
        ]))
        .all()
    }

    assert "uptrend_not_break_ma20" in rules
    r = rules["uptrend_not_break_ma20"]
    assert r.rule_type == "filter"
    assert r.timeframe == "daily"
    assert r.executor_key == "ma_trend"
    assert r.enabled is True

    assert "uptrend_break_ma20_consecutive_remove" in rules
    r2 = rules["uptrend_break_ma20_consecutive_remove"]
    assert r2.rule_type == "remove_signal"
    assert r2.timeframe == "daily"
    assert r2.executor_key == "break_ma"
    assert r2.enabled is True


def test_uptrend_bindings_created_by_seed(db_session):
    SeedService(db_session).init_defaults()

    bindings = {
        row.rule_code: row
        for row in db_session.query(TradingSystemRuleBinding)
        .filter(
            TradingSystemRuleBinding.system_code == "uptrend",
            TradingSystemRuleBinding.stage == "observe",
            TradingSystemRuleBinding.enabled.is_(True),
        )
        .all()
    }

    # New filter replaces near_ma20_pullback as required at sort_order=1
    assert "uptrend_not_break_ma20" in bindings
    b = bindings["uptrend_not_break_ma20"]
    assert b.required is True
    assert b.sort_order == 1
    signal = (b.config_json or {}).get("signal", {})
    assert signal.get("mode") == "price_not_below_ma"
    assert signal.get("ma") == 20

    # b5_divergence: sort_order=2, after_watch_added=True
    assert "b5_divergence" in bindings
    b5 = bindings["b5_divergence"]
    assert b5.required is False
    assert b5.sort_order == 2
    b5_signal = (b5.config_json or {}).get("signal", {})
    assert b5_signal.get("after_watch_added") is True

    # b15_divergence: sort_order=3, after_watch_added=True
    assert "b15_divergence" in bindings
    b15 = bindings["b15_divergence"]
    assert b15.required is False
    assert b15.sort_order == 3
    b15_signal = (b15.config_json or {}).get("signal", {})
    assert b15_signal.get("after_watch_added") is True

    # New remove_signal rule at sort_order=10
    assert "uptrend_break_ma20_consecutive_remove" in bindings
    rm = bindings["uptrend_break_ma20_consecutive_remove"]
    assert rm.required is False
    assert rm.sort_order == 10
    rm_signal = (rm.config_json or {}).get("signal", {})
    assert rm_signal.get("break_type") == "consecutive_below"
    assert rm_signal.get("ma") == 20
    assert rm_signal.get("consecutive_bars") == 3


def test_seed_idempotent_does_not_duplicate_uptrend_rules(db_session):
    first = SeedService(db_session).init_defaults()
    second = SeedService(db_session).init_defaults()

    created_second = second.get("created", 0)
    # After first seed, second should not create new rule definitions or bindings
    assert created_second == 0


def test_seed_preserves_existing_non_target_config(db_session):
    """Re-seeding does not overwrite user-modified fields on existing bindings."""
    SeedService(db_session).init_defaults()

    # Simulate a user customizing b5_divergence binding
    binding = db_session.query(TradingSystemRuleBinding).filter_by(
        system_code="uptrend", rule_code="b5_divergence", stage="observe"
    ).first()
    binding.required = True
    binding.sort_order = 99
    user_config = dict(binding.config_json or {})
    user_signal = dict(user_config.get("signal", {}))
    user_signal["custom_field"] = "user_value"
    user_config["signal"] = user_signal
    binding.config_json = user_config
    db_session.commit()

    # Re-seed
    SeedService(db_session).init_defaults()
    db_session.refresh(binding)

    # User customizations preserved
    assert binding.required is True
    assert binding.sort_order == 99
    # after_watch_added should still be True (seed adds it idempotently)
    updated_signal = (binding.config_json or {}).get("signal", {})
    assert updated_signal.get("after_watch_added") is True
    assert updated_signal.get("custom_field") == "user_value"


def test_seed_adds_after_watch_added_when_existing_binding_has_no_signal_config(db_session):
    SeedService(db_session).init_defaults()
    binding = db_session.query(TradingSystemRuleBinding).filter_by(
        system_code="uptrend", rule_code="b5_divergence", stage="observe"
    ).first()
    binding.config_json = {
        "data": {"timeframe": "5m", "lookback_bars": 120, "indicators": ["macd"]}
    }
    db_session.commit()

    SeedService(db_session).init_defaults()
    db_session.refresh(binding)

    assert binding.config_json["signal"]["after_watch_added"] is True
