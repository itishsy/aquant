from datetime import date

from app.services.hot_stock import HotStockService
from app.services.limit_up import LimitUpService
from app.services.sector import SectorService
from app.services.watch_pool import WatchPoolService


def test_auto_add_candidates_respects_blacklist(db_session):
    trade_date = date(2026, 4, 24)
    SectorService(db_session).collect_sector_daily(trade_date)
    LimitUpService(db_session).collect_limit_up_daily(trade_date)
    HotStockService(db_session).collect_hot_stock_rank(trade_date)
    service = WatchPoolService(db_session)
    service.mark_blacklist("300750.SZ", "test")
    service.auto_add_candidates(trade_date)
    codes = [item.stock_code for item in service.list_watch_pool()]
    assert "300750.SZ" not in codes
    assert codes
