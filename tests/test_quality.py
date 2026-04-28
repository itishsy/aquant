import pytest
from datetime import date, datetime

from app.services.quality import DataQualityError, DataQualityService


def test_validate_kline_daily_ok():
    payload = {
        "stock_code": "600000.SH",
        "trade_date": date(2026, 4, 24),
        "open": 10.0,
        "high": 10.5,
        "low": 9.8,
        "close": 10.2,
        "prev_close": 10.0,
        "change_pct": 2.0,
    }
    DataQualityService.validate_kline_daily(payload)


def test_validate_kline_raises():
    with pytest.raises(DataQualityError):
        DataQualityService.validate_kline_15m(
            {
                "stock_code": "600000.SH",
                "trade_time": datetime(2026, 4, 24, 10, 0),
                "open": 10.5,
                "high": 10.4,
                "low": 9.8,
                "close": 10.2,
                "prev_close": 10.0,
                "change_pct": 2.0,
            }
        )
