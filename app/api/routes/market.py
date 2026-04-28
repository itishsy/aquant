from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.market import MarketService

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/daily")
def get_market_daily(trade_date: date, db: Session = Depends(get_db)):
    service = MarketService(db)
    data = service.get_market_daily(trade_date) or service.collect_market_daily(trade_date)
    return data


@router.get("/summary")
def get_market_summary(db: Session = Depends(get_db)):
    service = MarketService(db)
    if not service.get_market_daily(date.today()):
        service.collect_market_daily(date.today())
    return service.get_market_summary()
