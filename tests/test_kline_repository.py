from datetime import datetime

from app.models import MktStockKline
from app.services.kline_repository import KlineRepository


def test_kline_repository_upsert_deduplicates_and_updates(db_session):
    repo = KlineRepository(db_session)
    rows = [
        {
            "kline_time": datetime(2026, 5, 22, 9, 35),
            "open": 10.0,
            "high": 10.5,
            "low": 9.9,
            "close": 10.2,
            "volume": 1000,
            "amount": 10200,
        }
    ]

    assert repo.upsert_rows("000001.SZ", "5m", rows, "mock") == 1
    assert repo.upsert_rows("000001.SZ", "5m", [{**rows[0], "close": 10.4}], "mock") == 1

    stored = db_session.query(MktStockKline).all()
    assert len(stored) == 1
    assert stored[0].stock_code == "sz000001"
    assert stored[0].timeframe == "5m"
    assert stored[0].trade_date.isoformat() == "2026-05-22"
    assert stored[0].close_price == 10.4


def test_kline_repository_queries_are_scoped_by_timeframe(db_session):
    repo = KlineRepository(db_session)
    repo.upsert_rows(
        "000001.SZ",
        "5m",
        [
            {"kline_time": datetime(2026, 5, 22, 9, 35), "open": 10, "high": 11, "low": 9, "close": 10.1},
            {"kline_time": datetime(2026, 5, 22, 9, 40), "open": 10.1, "high": 11, "low": 9, "close": 10.2},
            {"kline_time": datetime(2026, 5, 22, 9, 45), "open": 10.2, "high": 11, "low": 9, "close": 10.3},
        ],
        "mock",
    )
    repo.upsert_rows(
        "000001.SZ",
        "15m",
        [{"kline_time": datetime(2026, 5, 22, 9, 45), "open": 20, "high": 21, "low": 19, "close": 20.1}],
        "mock",
    )

    bars = repo.get_recent_bars("000001.SZ", "5m", 2)

    assert [bar.kline_time for bar in bars] == [datetime(2026, 5, 22, 9, 40), datetime(2026, 5, 22, 9, 45)]
    assert [bar.close_price for bar in bars] == [10.2, 10.3]
    assert repo.latest_time("000001.SZ", "5m") == datetime(2026, 5, 22, 9, 45)
    assert repo.count_recent_bars("000001.SZ", "5m") == 3
    assert repo.count_recent_bars("000001.SZ", "5m", since=datetime(2026, 5, 22, 9, 40)) == 2
    assert repo.count_recent_bars("000001.SZ", "15m") == 1


def test_kline_repository_accepts_daily_rows_with_trade_date(db_session):
    repo = KlineRepository(db_session)

    repo.upsert_rows(
        "000001.SZ",
        "daily",
        [{"trade_date": "2026-05-22", "open_price": 10, "high_price": 11, "low_price": 9, "close_price": 10.5}],
        "mock",
    )

    bar = repo.get_recent_bars("000001.SZ", "daily", 1)[0]
    assert bar.kline_time == datetime(2026, 5, 22)
    assert bar.trade_date.isoformat() == "2026-05-22"
