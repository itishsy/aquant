from datetime import date

from app.services.hot_stock import HotStockService
from app.services.limit_up import LimitUpService
from app.services.prd_v1 import PrdWatchPoolService
from app.services.sector import SectorService
from app.services.watch_pool import WatchPoolService


def test_auto_add_candidates_is_disabled_by_prd_v1(db_session):
    trade_date = date(2026, 4, 24)
    SectorService(db_session).collect_sector_daily(trade_date)
    LimitUpService(db_session).collect_limit_up_daily(trade_date)
    HotStockService(db_session).collect_hot_stock_rank(trade_date)
    service = WatchPoolService(db_session)
    service.mark_blacklist("300750.SZ", "test")
    added = service.auto_add_candidates(trade_date)
    codes = [item.stock_code for item in service.list_watch_pool()]
    assert added == []
    assert "300750.SZ" not in codes
    assert codes == []


def test_manual_add_watch_creates_status_log(db_session):
    service = PrdWatchPoolService(db_session)
    item = service.add_watch(
        {
            "stock_code": "603019.SH",
            "stock_name": "中科曙光",
            "labels": ["人气"],
            "operation_strategies": ["趋势交易"],
            "buy_point_types": ["B15 底背离买点"],
            "source_type": "hot_stock",
            "source_platform": "mock",
            "source_rank": 1,
            "source_score": 98,
            "source_reason": "用户从市场页手动加入",
        }
    )
    assert item.pool_status == "观察中"
    assert item.monitor_enabled is True
    assert service.logs(item.id)
