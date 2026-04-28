from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.sector import SectorService

router = APIRouter(prefix="/sectors", tags=["sectors"])


@router.get("/top")
def top_sectors(trade_date: date, limit: int = 3, db: Session = Depends(get_db)):
    service = SectorService(db)
    if not service.get_top_sectors(trade_date, 1):
        service.collect_sector_daily(trade_date)
    return service.get_top_sectors(trade_date, limit)
