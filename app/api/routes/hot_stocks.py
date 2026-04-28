from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.hot_stock import HotStockService

router = APIRouter(prefix="/hot-stocks", tags=["hot-stocks"])


@router.get("/top")
def top_hot_stocks(trade_date: date, limit: int = 10, db: Session = Depends(get_db)):
    service = HotStockService(db)
    if not service.get_top_hot_stocks(trade_date, 1):
        service.collect_hot_stock_rank(trade_date)
    return service.get_top_hot_stocks(trade_date, limit)
