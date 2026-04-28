from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import BlacklistPayload, WatchPoolCreate, WatchPoolUpdateLabels
from app.services.watch_pool import WatchPoolService

router = APIRouter(prefix="/watch-pool", tags=["watch-pool"])


@router.get("")
def list_watch_pool(label: str | None = None, db: Session = Depends(get_db)):
    return WatchPoolService(db).list_watch_pool({"label": label} if label else None)


@router.post("")
def create_watch_pool(payload: WatchPoolCreate, db: Session = Depends(get_db)):
    return WatchPoolService(db).add_to_watch_pool(
        payload.stock_code, payload.reason, payload.labels, payload.strategy_type
    )


@router.patch("/{stock_code}/labels")
def update_watch_pool_labels(stock_code: str, payload: WatchPoolUpdateLabels, db: Session = Depends(get_db)):
    return WatchPoolService(db).update_labels(stock_code, payload.labels)


@router.post("/{stock_code}/blacklist")
def blacklist_watch_pool(stock_code: str, payload: BlacklistPayload, db: Session = Depends(get_db)):
    return WatchPoolService(db).mark_blacklist(stock_code, payload.reason)


@router.delete("/{stock_code}")
def remove_watch_pool(stock_code: str, reason: str = "manual", db: Session = Depends(get_db)):
    WatchPoolService(db).remove_from_watch_pool(stock_code, reason)
    return {"message": "ok"}
