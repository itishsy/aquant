from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.models import MktStockQuote, WatchPool, WatchSignal, WatchTrade, WatchTradeExecution
from app.services.prd_v1 import SeedService


def _local_now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().timezone))


def _watch(code: str, name: str, *, status: str = "watching", active: bool = True, created_at: datetime) -> WatchPool:
    return WatchPool(
        stock_code=code,
        stock_name=name,
        sector_name="测试板块",
        status=status,
        active=active,
        monitor_enabled=True,
        signal_enabled=True,
        trading_system="uptrend",
        trading_system_code="uptrend",
        system_stage="trading" if status == "trading" else "observe",
        created_at=created_at,
        updated_at=created_at,
    )


def _signal(watch: WatchPool, *, code: str, when: datetime, status: str = "pending") -> WatchSignal:
    return WatchSignal(
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        signal_type="buy",
        buy_point_type=code,
        rule_code=code,
        rule_type="buy_signal",
        strategy_name=f"rule_executor:{code}",
        trigger_date=when.date(),
        trigger_time=when,
        signal_status=status,
        trading_system_code="uptrend",
    )


def test_watch_overview_orders_groups_and_returns_summary(client, db_session):
    SeedService(db_session).init_defaults()
    now = _local_now().replace(tzinfo=None, microsecond=0)
    yesterday = now - timedelta(days=1)

    trading = _watch("000001.SZ", "交易中", status="trading", created_at=yesterday - timedelta(days=5))
    pending = _watch("000002.SZ", "今日待处理", created_at=yesterday - timedelta(days=4))
    signaled = _watch("000003.SZ", "今日信号", created_at=yesterday - timedelta(days=3))
    watching_new = _watch("000004.SZ", "观察较新", created_at=yesterday)
    watching_old = _watch("000005.SZ", "观察较旧", created_at=yesterday - timedelta(days=2))
    removed = _watch("000006.SZ", "已剔除", status="removed", active=False, created_at=yesterday - timedelta(days=8))
    removed.removed_at = yesterday - timedelta(hours=1)
    db_session.add_all([trading, pending, signaled, watching_new, watching_old, removed])
    db_session.flush()

    pending_signal = _signal(pending, code="b5_divergence", when=now - timedelta(minutes=5), status="buy_pending_confirm")
    normal_signal = _signal(signaled, code="b15_divergence", when=now - timedelta(minutes=2), status="generated")
    trade = WatchTrade(
        watch_id=trading.id,
        stock_code=trading.stock_code,
        stock_name=trading.stock_name,
        trading_system_code="uptrend",
        trade_status="holding",
        current_stage="trading",
        stop_loss_price=9.5,
        target_price=12.0,
        created_at=yesterday,
        updated_at=now - timedelta(minutes=10),
    )
    db_session.add_all([pending_signal, normal_signal, trade])
    db_session.flush()
    db_session.add(
        WatchTradeExecution(
            trade_id=trade.id,
            watch_id=trading.id,
            stock_code=trading.stock_code,
            stock_name=trading.stock_name,
            execution_type="buy",
            execution_time=datetime.now(timezone.utc).replace(tzinfo=None),
            execution_price=10.0,
            execution_amount=100,
            execution_reason="测试买入",
        )
    )
    db_session.add(MktStockQuote(stock_code=trading.stock_code, stock_name=trading.stock_name, latest_price=10.5, change_pct=2.5))
    db_session.commit()

    response = client.get("/api/h5/watch-pool/overview")
    assert response.status_code == 200
    payload = response.json()["data"]
    rows = payload["items"]

    assert [row["stock_name"] for row in rows] == [
        "交易中",
        "今日待处理",
        "今日信号",
        "观察较新",
        "观察较旧",
        "已剔除",
    ]
    assert [row["sort_priority"] for row in rows] == [10, 20, 30, 40, 40, 90]
    assert [row["display_group"] for row in rows] == [
        "trading",
        "today_signal",
        "today_signal",
        "watching",
        "watching",
        "terminal",
    ]
    assert rows[0]["active_trade"]["trade_status"] == "holding"
    assert rows[0]["latest_price"] == 10.5
    assert rows[1]["latest_signal"]["rule_name"] == "5分钟底背离"
    assert payload["summary"] == {
        "total": 6,
        "active_total": 5,
        "terminal_total": 1,
        "today_signal_count": 2,
        "today_trade_count": 1,
    }


def test_watch_overview_include_terminal_false_and_filters(client, db_session):
    now = _local_now().replace(tzinfo=None, microsecond=0)
    active = _watch("600001.SH", "活动自选", created_at=now)
    removed = _watch("600002.SH", "已剔除", status="removed", active=False, created_at=now - timedelta(days=1))
    db_session.add_all([active, removed])
    db_session.commit()

    response = client.get("/api/h5/watch-pool/overview", params={"include_terminal": "false"})
    assert response.status_code == 200
    assert [row["stock_name"] for row in response.json()["data"]["items"]] == ["活动自选"]

    filtered = client.get("/api/h5/watch-pool/overview", params={"keyword": "剔除", "status": "removed"})
    assert filtered.status_code == 200
    assert [row["stock_name"] for row in filtered.json()["data"]["items"]] == ["已剔除"]


def test_watch_overview_handles_missing_related_data(client, db_session):
    now = _local_now().replace(tzinfo=None, microsecond=0)
    db_session.add(_watch("300001.SZ", "无关联数据", created_at=now))
    db_session.commit()

    response = client.get("/api/h5/watch-pool/overview")
    assert response.status_code == 200
    row = response.json()["data"]["items"][0]
    assert row["latest_signal"] is None
    assert row["active_trade"] is None
    assert row["latest_price"] is None


def test_watch_overview_prefers_explicit_watch_signal_over_newer_legacy_signal(client, db_session):
    SeedService(db_session).init_defaults()
    now = _local_now().replace(tzinfo=None, microsecond=0)
    watch = _watch("300002.SZ", "明确关联优先", created_at=now - timedelta(days=1))
    db_session.add(watch)
    db_session.flush()
    direct = _signal(watch, code="b5_divergence", when=now - timedelta(minutes=10), status="pending")
    legacy = _signal(watch, code="b15_divergence", when=now - timedelta(minutes=1), status="pending")
    legacy.watch_id = None
    db_session.add_all([direct, legacy])
    db_session.commit()

    response = client.get("/api/h5/watch-pool/overview")
    assert response.status_code == 200
    row = response.json()["data"]["items"][0]
    assert row["latest_signal"]["signal_id"] == direct.signal_id
    assert row["latest_signal"]["rule_name"] == "5分钟底背离"
