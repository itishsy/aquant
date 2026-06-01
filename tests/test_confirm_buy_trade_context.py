from datetime import date, datetime

from app.models import WatchPool, WatchSignal, WatchTrade
from app.services.prd_v1 import SeedService


def test_confirm_buy_trade_inherits_system_context(client, db_session):
    SeedService(db_session).init_defaults()
    watch = WatchPool(
        stock_code="603019.SH",
        stock_name="中科曙光",
        status="buy_pending_confirm",
        active=True,
        monitor_enabled=True,
        signal_enabled=True,
        trading_system="breakout",
        trading_system_code="breakout",
        system_stage="observe",
        system_params_json={
            "platform_upper_price": 24.0,
            "platform_support_price": 23.0,
            "key_observe_price": 24.5,
            "invalid_condition": "跌破平台支撑",
        },
    )
    db_session.add(watch)
    db_session.flush()
    signal = WatchSignal(
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        signal_type="buy",
        buy_point_type="b15_divergence",
        trading_system="breakout",
        trading_system_code="breakout",
        rule_code="b15_divergence",
        rule_type="buy_signal",
        strategy_name="rule_executor:macd_bottom_divergence",
        signal_level="A",
        trigger_time=datetime(2026, 5, 24, 10, 30),
        trigger_date=date(2026, 5, 24),
        trigger_price=25.05,
        trigger_reason="15m bottom divergence",
        signal_status="buy_pending_confirm",
        user_action="pending",
    )
    db_session.add(signal)
    db_session.commit()

    response = client.post(
        f"/api/h5/watch-signals/{signal.signal_id}/confirm-buy",
        json={
            "buy_price": 25.1,
            "amount": 100,
            "stop_loss_price": 23.0,
            "buy_point_confirmed": True,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trading_system_code"] == "breakout"
    assert data["entry_rule_code"] == "b15_divergence"
    assert data["current_stage"] == "trading"
    assert "m5_top_divergence" in data["active_sell_rule_codes_json"]
    assert "m30_dead_cross" in data["active_sell_rule_codes_json"]
    assert "break_platform_support" in data["active_stop_rule_codes_json"]
    assert data["system_params_json"]["platform_upper_price"] == 24.0
    assert data["latest_trade_signal_id"] == signal.signal_id

    db_session.refresh(watch)
    db_session.refresh(signal)
    trade = db_session.query(WatchTrade).filter(WatchTrade.signal_id == signal.signal_id).first()
    assert trade is not None
    assert signal.signal_status == "confirmed_buy"
    assert signal.user_action == "confirmed_buy"
    assert watch.system_stage == "trading"
    assert watch.status == "trading"
    assert watch.monitor_enabled is False
    assert watch.signal_enabled is False
