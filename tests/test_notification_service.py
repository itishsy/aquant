from datetime import datetime

from app.models import WatchSignal
from app.services.notification import NotificationService


def test_buy_signal_notification_records_disabled_error():
    signal = WatchSignal(
        watch_id=1,
        stock_code="603019.SH",
        stock_name="中科曙光",
        signal_type="buy",
        buy_point_type="b15_divergence",
        trading_system="breakout",
        trading_system_code="breakout",
        rule_code="b15_divergence",
        rule_type="buy_signal",
        strategy_name="rule_executor:macd_bottom_divergence",
        trigger_time=datetime(2026, 5, 24, 10, 30),
        trigger_date=datetime(2026, 5, 24).date(),
        trigger_price=25.05,
        trigger_reason="15m bottom divergence",
        signal_status="buy_pending_confirm",
    )

    result = NotificationService().notify_buy_signal(
        signal,
        trading_system_name="突破",
        rule_name="15分钟底背离",
    )

    assert result.sent is False
    assert "email notification is disabled" in result.error
    assert signal.notification_sent is False
    assert signal.notification_error == result.error
