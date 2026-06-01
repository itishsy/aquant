from app.models import (
    ConfigTask,
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
    assert {
        "platform_upper_price",
        "platform_support_price",
        "key_observe_price",
        "invalid_condition",
    } <= required_params

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
        ("observe", "not_break_platform_upper"),
        ("observe", "b5_divergence"),
        ("observe", "b15_divergence"),
        ("trading", "m5_top_divergence"),
        ("trading", "m30_dead_cross"),
        ("stop_loss", "break_platform_support"),
    } <= stage_rules

    task_names = {row.task_name for row in db_session.query(ConfigTask).all()}
    assert {"scan_watch_rules", "scan_trade_rules"} <= task_names


def test_scheduler_registers_trading_system_rule_jobs():
    scheduler = build_scheduler()

    job_ids = {job.id for job in scheduler.get_jobs()}

    assert {
        "collect_all_market",
        "update_watch_prices",
        "scan_watch_signals",
        "auto_remove_watch_pool",
        "scan_watch_rules",
        "scan_trade_rules",
    } <= job_ids
    assert scheduler.get_job("scan_watch_rules").trigger.interval.total_seconds() == 600
    assert scheduler.get_job("scan_trade_rules").trigger.interval.total_seconds() == 600


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


def test_add_watch_with_trading_system_validates_required_params(client, db_session):
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

    assert response.status_code == 400
    assert "invalid_condition" in response.json()["detail"]
    assert db_session.query(WatchPool).count() == 0
