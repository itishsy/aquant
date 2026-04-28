from datetime import date, datetime

from app.models import SignalRecord
from app.services.review import ReviewService
from app.services.trade import TradeService


def create_signal(db_session) -> SignalRecord:
    signal = SignalRecord(
        stock_code="603019.SH",
        stock_name="中科曙光",
        sector_name="算力",
        signal_type="buy",
        signal_text="买入观察信号",
        strategy_name="mock",
        signal_level="A",
        trigger_time=datetime(2026, 4, 24, 10, 0),
        current_price=25.0,
        trigger_reason="测试信号",
        risk_desc="仅作为交易辅助",
        invalid_condition="跌破支撑位失效",
        market_status="修复",
        raw_snapshot={"x": 1},
    )
    db_session.add(signal)
    db_session.commit()
    db_session.refresh(signal)
    return signal


def test_confirm_trade_and_sell_and_review(db_session):
    signal = create_signal(db_session)
    trade = TradeService(db_session).confirm_trade(
        signal.id,
        {
            "price": 25.0,
            "quantity": 100,
            "position": 0.2,
            "stop_loss_price": 23.5,
            "target_price": 27.0,
            "trade_plan": "遵守计划，仅作为交易辅助",
        },
    )
    sold = TradeService(db_session).sell_trade(trade.id, {"price": 26.0, "quantity": 100, "reason": "test"})
    assert sold.realized_pnl == 100.0

    weekly = ReviewService(db_session).generate_weekly_review(date(2026, 4, 21), date(2026, 4, 27))
    assert "total_trades" in weekly.metrics
    assert "不构成收益承诺" in weekly.system_summary


def test_daily_plan_and_weekly_note_api(client):
    create_plan_response = client.post(
        "/api/reviews/daily-plans",
        json={
            "plan_date": "2026-04-26",
            "title": "盘前计划",
            "focus": "算力修复",
            "risk_rule": "转弱不追高",
            "note": "仅观察核心股",
        },
    )
    assert create_plan_response.status_code == 200
    assert create_plan_response.json()["title"] == "盘前计划"

    list_response = client.get("/api/reviews/daily-plans?start_date=2026-04-20&end_date=2026-04-27")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    weekly_note_response = client.post(
        "/api/reviews/weekly/note",
        json={
            "week_start": "2026-04-21",
            "week_end": "2026-04-27",
            "user_notes": "本周严格执行计划，仅作为交易辅助。",
        },
    )
    assert weekly_note_response.status_code == 200
    assert weekly_note_response.json()["user_notes"] == "本周严格执行计划，仅作为交易辅助。"
