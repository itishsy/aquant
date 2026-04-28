from datetime import date

from app.models import MarketDaily
from app.services.hot_stock import HotStockService
from app.services.kline import KlineService
from app.services.limit_up import LimitUpService
from app.services.market import MarketService
from app.services.sector import SectorService
from app.services.signal_engine import SignalEngine
from app.services.watch_pool import WatchPoolService


def seed_signal_context(db_session, candle_session, trade_date=date(2026, 4, 24), market_date=None):
    MarketService(db_session).collect_market_daily(market_date or trade_date)
    SectorService(db_session).collect_sector_daily(trade_date)
    LimitUpService(db_session).collect_limit_up_daily(trade_date)
    HotStockService(db_session).collect_hot_stock_rank(trade_date)
    watch = WatchPoolService(db_session).add_to_watch_pool(
        "603019.SH",
        "manual setup",
        ["core"],
        "manual",
    )
    watch.stock_name = "中科曙光"
    watch.sector_name = "算力"
    db_session.commit()
    KlineService(candle_session).collect_daily_kline("603019.SH", date(2026, 3, 1), trade_date)
    return watch


def test_macd_signal_generated(db_session, candle_session):
    seed_signal_context(db_session, candle_session)
    signals = SignalEngine(db_session, candle_session).scan("macd_15m_bullish_divergence")
    assert signals
    assert signals[0].signal_text == "买入观察信号"
    assert signals[0].raw_snapshot


def test_market_downturn_blocks_buy_signal(db_session, candle_session):
    trade_date = date(2026, 4, 24)
    seed_signal_context(db_session, candle_session, trade_date)
    market = db_session.query(MarketDaily).first()
    market.market_status = "冰点"
    db_session.commit()
    signals = SignalEngine(db_session, candle_session).scan("macd_15m_bullish_divergence")
    assert not signals
