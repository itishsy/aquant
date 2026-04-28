from datetime import date

from app.services.hot_stock import HotStockService
from app.services.limit_up import LimitUpService
from app.services.sector import SectorService


def test_hot_stock_top10(db_session):
    trade_date = date(2026, 4, 24)
    SectorService(db_session).collect_sector_daily(trade_date)
    LimitUpService(db_session).collect_limit_up_daily(trade_date)
    service = HotStockService(db_session)
    service.collect_hot_stock_rank(trade_date)
    items = service.get_top_hot_stocks(trade_date, 10)
    assert items
    assert items[0]["total_score"] >= items[-1]["total_score"]
