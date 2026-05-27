from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.services.kline_collection import KlineCollectionService, KlineFreshnessService
from app.services.kline_repository import KlineRepository


class FakeProvider:
    def __init__(self):
        self.daily_calls = []
        self.intraday_calls = []

    def get_daily_kline(self, stock_code, start_date, end_date):
        self.daily_calls.append((stock_code, start_date, end_date))
        return [
            {
                "trade_date": end_date,
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10.5,
                "volume": 1000,
                "amount": 10500,
                "source": "fake",
            }
        ]

    def get_intraday_kline(self, stock_code, interval, start_time, end_time):
        self.intraday_calls.append((stock_code, interval, start_time, end_time))
        return [
            {
                "trade_time": end_time,
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10.5,
                "volume": 1000,
                "amount": 10500,
                "source": "fake",
            }
        ]


def test_freshness_hit_skips_provider(db_session):
    repo = KlineRepository(db_session)
    repo.upsert_rows(
        "000001.SZ",
        "5m",
        [{"kline_time": datetime(2026, 5, 22, 10, 15), "open": 10, "high": 11, "low": 9, "close": 10.5}],
        "fake",
    )
    provider = FakeProvider()
    service = KlineCollectionService(db_session, provider=provider, now=datetime(2026, 5, 22, 10, 17))

    affected = service.collect_for_requirements(
        {"000001.SZ": {"5m": {"timeframe": "5m", "lookback_bars": 120, "indicators": ["macd"], "reasons": ["b5"]}}}
    )

    assert affected == 0
    assert provider.intraday_calls == []
    assert service.error_summary() == ""


def test_missing_intraday_calls_provider_and_writes_rows(db_session):
    provider = FakeProvider()
    service = KlineCollectionService(db_session, provider=provider, now=datetime(2026, 5, 22, 10, 17))

    affected = service.collect_for_requirements(
        {"000001.SZ": {"5m": {"timeframe": "5m", "lookback_bars": 120, "indicators": ["macd"], "reasons": ["b5"]}}}
    )

    assert affected == 1
    assert len(provider.intraday_calls) == 1
    assert provider.intraday_calls[0][1] == "5m"
    assert KlineRepository(db_session).count_recent_bars("000001.SZ", "5m") == 1


def test_same_stock_timeframe_does_not_duplicate_rows(db_session):
    provider = FakeProvider()
    service = KlineCollectionService(db_session, provider=provider, now=datetime(2026, 5, 22, 10, 17))
    requirements = {
        "000001.SZ": {
            "5m": {"timeframe": "5m", "lookback_bars": 120, "indicators": ["macd"], "reasons": ["b5", "m5"]}
        }
    }

    first = service.collect_for_requirements(requirements)
    second = service.collect_for_requirements(requirements)

    assert first == 1
    assert second == 0
    assert len(provider.intraday_calls) == 1
    assert KlineRepository(db_session).count_recent_bars("000001.SZ", "5m") == 1


def test_daily_expected_after_close(db_session):
    repo = KlineRepository(db_session)
    freshness = KlineFreshnessService(repo)

    assert freshness.expected_latest_time("daily", datetime(2026, 5, 22, 14, 59)) is None
    assert freshness.expected_latest_time("daily", datetime(2026, 5, 22, 15, 1)) == datetime(2026, 5, 22)


def test_expected_latest_time_uses_shanghai_timezone_for_intraday(db_session):
    repo = KlineRepository(db_session)
    freshness = KlineFreshnessService(repo)
    shanghai = ZoneInfo("Asia/Shanghai")

    assert freshness.expected_latest_time("5m", datetime(2026, 5, 27, 10, 17, tzinfo=shanghai)) == datetime(
        2026, 5, 27, 10, 15
    )
    assert freshness.expected_latest_time("15m", datetime(2026, 5, 27, 14, 46, tzinfo=shanghai)) == datetime(
        2026, 5, 27, 14, 45
    )
    assert freshness.expected_latest_time("5m", datetime(2026, 5, 27, 8, 0, tzinfo=shanghai)) is None


def test_daily_expected_latest_time_uses_shanghai_timezone(db_session):
    repo = KlineRepository(db_session)
    freshness = KlineFreshnessService(repo)
    shanghai = ZoneInfo("Asia/Shanghai")

    assert freshness.expected_latest_time("daily", datetime(2026, 5, 27, 15, 10, tzinfo=shanghai)) == datetime(
        2026, 5, 27
    )


def test_missing_daily_calls_provider(db_session):
    provider = FakeProvider()
    service = KlineCollectionService(db_session, provider=provider, now=datetime(2026, 5, 22, 15, 1))

    affected = service.collect_for_requirements(
        {"000001.SZ": {"daily": {"timeframe": "daily", "lookback_bars": 5, "indicators": [], "reasons": ["break"]}}}
    )

    assert affected == 1
    assert provider.daily_calls[0][0] == "000001.SZ"
    assert provider.daily_calls[0][2] == date(2026, 5, 22)
    assert KlineRepository(db_session).latest_time("000001.SZ", "daily") == datetime(2026, 5, 22)
