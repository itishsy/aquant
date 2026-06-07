from datetime import datetime, timedelta

from app.models import WatchPool, WatchSignal, WatchTrade, WatchTradeExecution
from app.services.prd_v1 import SeedService


def _signal(
    *,
    stock_code: str,
    stock_name: str,
    rule_code: str,
    when: datetime,
    watch_id: int | None,
) -> WatchSignal:
    return WatchSignal(
        watch_id=watch_id,
        stock_code=stock_code,
        stock_name=stock_name,
        signal_type="buy",
        buy_point_type=rule_code,
        rule_code=rule_code,
        rule_type="buy_signal",
        strategy_name=f"rule_executor:{rule_code}",
        trigger_date=when.date(),
        trigger_time=when,
        signal_status="pending",
        trading_system_code="uptrend",
    )


def test_watch_signal_history_orders_and_supports_legacy_rows(client, db_session):
    SeedService(db_session).init_defaults()
    watch = WatchPool(stock_code="000001.SZ", stock_name="目标股票", status="watching", active=True)
    other = WatchPool(stock_code="000002.SZ", stock_name="其他股票", status="watching", active=True)
    db_session.add_all([watch, other])
    db_session.flush()
    base = datetime(2026, 6, 1, 10, 0)
    direct = _signal(stock_code=watch.stock_code, stock_name=watch.stock_name, rule_code="b5_divergence", when=base, watch_id=watch.id)
    legacy = _signal(stock_code=watch.stock_code, stock_name=watch.stock_name, rule_code="b15_divergence", when=base + timedelta(hours=1), watch_id=None)
    unrelated = _signal(stock_code=other.stock_code, stock_name=other.stock_name, rule_code="observe_break_ma5", when=base + timedelta(hours=2), watch_id=None)
    db_session.add_all([direct, legacy, unrelated])
    db_session.commit()

    response = client.get(f"/api/h5/watch-pool/{watch.id}/signals")
    assert response.status_code == 200
    rows = response.json()["data"]
    assert [row["signal_id"] for row in rows] == [legacy.signal_id, direct.signal_id]
    assert [row["rule_name"] for row in rows] == ["15分钟底背离", "5分钟底背离"]
    assert all(row["stock_code"] == watch.stock_code for row in rows)


def test_watch_trade_records_order_executions_and_include_summary(client, db_session):
    watch = WatchPool(stock_code="600001.SH", stock_name="交易目标", status="trading", active=True)
    other = WatchPool(stock_code="600002.SH", stock_name="其他交易", status="trading", active=True)
    db_session.add_all([watch, other])
    db_session.flush()
    base = datetime(2026, 6, 1, 9, 30)
    direct_trade = WatchTrade(
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        trade_status="completed",
        first_buy_time=base,
        first_buy_price=10,
        total_buy_amount=100,
        remaining_amount=0,
        created_at=base,
    )
    legacy_trade = WatchTrade(
        watch_id=None,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        trade_status="open",
        first_buy_time=base + timedelta(days=1),
        first_buy_price=11,
        total_buy_amount=50,
        remaining_amount=50,
        buy_reason="旧交易概要",
        created_at=base + timedelta(days=1),
    )
    unrelated_trade = WatchTrade(
        watch_id=other.id,
        stock_code=other.stock_code,
        stock_name=other.stock_name,
        trade_status="open",
        created_at=base,
    )
    db_session.add_all([direct_trade, legacy_trade, unrelated_trade])
    db_session.flush()
    buy = WatchTradeExecution(
        trade_id=direct_trade.id,
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        execution_type="buy",
        execution_time=base,
        execution_price=10,
        execution_amount=100,
        execution_reason="买入原因",
    )
    sell = WatchTradeExecution(
        trade_id=direct_trade.id,
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        execution_type="stop_loss",
        execution_time=base + timedelta(hours=4),
        execution_price=9,
        execution_amount=100,
        execution_reason="跌破MA20",
    )
    db_session.add_all([buy, sell])
    db_session.commit()

    response = client.get(f"/api/h5/watch-pool/{watch.id}/trade-records")
    assert response.status_code == 200
    rows = response.json()["data"]
    assert [row["record_type"] for row in rows] == ["trade_summary", "execution", "execution"]
    assert rows[1]["execution_type_name"] == "止损"
    assert rows[1]["execution_reason"] == "跌破MA20"
    assert rows[2]["execution_type_name"] == "买入"
    assert all(row["trade_id"] != unrelated_trade.id for row in rows)


def test_watch_history_empty_and_not_found(client, db_session):
    watch = WatchPool(stock_code="300001.SZ", stock_name="暂无历史", status="watching", active=True)
    db_session.add(watch)
    db_session.commit()

    assert client.get(f"/api/h5/watch-pool/{watch.id}/signals").json()["data"] == []
    assert client.get(f"/api/h5/watch-pool/{watch.id}/trade-records").json()["data"] == []
    assert client.get("/api/h5/watch-pool/999999/signals").status_code == 404
    assert client.get("/api/h5/watch-pool/999999/trade-records").status_code == 404
