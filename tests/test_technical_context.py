from datetime import datetime, timedelta

from app.rule_executors import RuleContext
from app.services.kline_repository import KlineRepository
from app.services.technical_context import TechnicalContextService


def test_technical_context_returns_bars_and_macd(db_session):
    repo = KlineRepository(db_session)
    start = datetime(2026, 5, 22, 9, 35)
    rows = []
    for idx in range(30):
        close = 10 + idx * 0.1
        rows.append(
            {
                "kline_time": start + timedelta(minutes=5 * idx),
                "open": close - 0.05,
                "high": close + 0.1,
                "low": close - 0.1,
                "close": close,
                "volume": 1000 + idx,
            }
        )
    repo.upsert_rows("000001.SZ", "5m", rows, "mock")

    context = TechnicalContextService(db_session).get_context("000001.SZ", "5m", 30, ["macd"])

    assert context["status"] == "ok"
    assert len(context["bars"]) == 30
    assert context["freshness"]["enough_bars"] is True
    assert context["freshness"]["latest_kline_time"] == (start + timedelta(minutes=145)).isoformat()
    assert set(context["indicators"]["macd"]) == {"dif", "dea", "hist"}
    assert len(context["indicators"]["macd"]["hist"]) == 30


def test_technical_context_reports_insufficient_bars(db_session):
    repo = KlineRepository(db_session)
    repo.upsert_rows(
        "000001.SZ",
        "15m",
        [{"kline_time": datetime(2026, 5, 22, 9, 45), "open": 10, "high": 11, "low": 9, "close": 10.5}],
        "mock",
    )

    context = TechnicalContextService(db_session).get_context("000001.SZ", "15m", 8, ["macd", "ma"])

    assert context["status"] == "insufficient_bars"
    assert context["freshness"]["bar_count"] == 1
    assert context["freshness"]["required_bars"] == 8
    assert context["freshness"]["enough_bars"] is False
    assert "Need 8 bars" in context["reason"]
    assert context["indicators"] == {}


def test_rule_context_accepts_technical_context():
    context = RuleContext(
        watch_id=1,
        stock_code="000001.SZ",
        stock_name="Ping An",
        trading_system_code="platform_breakout",
        stage="observe",
        technical={"status": "ok", "bars": [], "indicators": {}},
    )

    assert context.technical["status"] == "ok"
    assert context.rule_config == {}
