from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import LimitUpDaily
from app.services.limit_up import LimitUpService

router = APIRouter(prefix="/limit-up", tags=["limit-up"])


@router.get("/list")
def get_limit_up_list(trade_date: date, db: Session = Depends(get_db)):
    service = LimitUpService(db)
    existing = db.query(LimitUpDaily).filter(LimitUpDaily.trade_date == trade_date).all()
    if not existing:
        existing = service.collect_limit_up_daily(trade_date)
    return existing


@router.get("/summary")
def get_limit_up_summary(trade_date: date, db: Session = Depends(get_db)):
    service = LimitUpService(db)
    service.collect_limit_up_daily(trade_date)
    return service.generate_limit_up_summary(trade_date)
