from datetime import date

from app.services.market import MarketService


def test_market_score_ranges(db_session):
    strong, status_strong = MarketService.calculate_market_score(
        {
            "sh_index": 3400,
            "up_ratio": 0.9,
            "limit_up_count": 90,
            "max_continue_board": 6,
            "limit_down_count": 0,
            "broken_limit_ratio": 0.02,
            "total_amount": 20000,
        }
    )
    weak, status_weak = MarketService.calculate_market_score(
        {
            "sh_index": 2800,
            "up_ratio": 0.2,
            "limit_up_count": 10,
            "max_continue_board": 1,
            "limit_down_count": 12,
            "broken_limit_ratio": 0.6,
            "total_amount": 2000,
        }
    )
    assert strong >= 80
    assert status_strong == "强势"
    assert weak < 50
    assert status_weak in {"退潮", "冰点"}


def test_market_collect_and_summary(db_session):
    service = MarketService(db_session)
    data = service.collect_market_daily(date(2026, 4, 24))
    assert data.market_status in {"强势", "修复", "震荡", "退潮", "冰点"}
    summary = service.get_market_summary()
    assert "market_score" in summary
