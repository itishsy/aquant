from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_candle_db
from app.services.indicator import IndicatorService
from app.services.kline import KlineService
from app.services.normalization import xueqiu_link

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{stock_code}/kline/daily")
def get_daily_kline(stock_code: str, limit: int = 100, db: Session = Depends(get_candle_db)):
    rows = KlineService(db).get_daily_kline(stock_code, limit)
    closes = [row.close for row in rows]
    return {
        "stock_code": stock_code,
        "xueqiu_link": xueqiu_link(stock_code),
        "items": rows,
        "ma5": IndicatorService.calculate_ma(closes, 5),
        "ma20": IndicatorService.calculate_ma(closes, 20),
    }


@router.get("/{stock_code}/kline/15m")
def get_15m_kline(stock_code: str, limit: int = 200, db: Session = Depends(get_candle_db)):
    rows = KlineService(db).get_15m_kline(stock_code, limit)
    closes = [row.close for row in rows]
    return {
        "stock_code": stock_code,
        "xueqiu_link": xueqiu_link(stock_code),
        "items": rows,
        "macd": IndicatorService.calculate_macd(closes),
    }
