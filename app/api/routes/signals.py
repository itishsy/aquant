from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import SignalRecord
from app.schemas.common import TradeConfirmPayload
from app.services.signal_engine import SignalEngine
from app.services.trade import TradeService

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("")
def list_signals(db: Session = Depends(get_db)):
    return db.query(SignalRecord).order_by(SignalRecord.trigger_time.desc()).all()


@router.post("/scan")
def scan_signals(db: Session = Depends(get_db)):
    return SignalEngine(db).scan()


@router.post("/{signal_id}/confirm-trade")
def confirm_trade(signal_id: int, payload: TradeConfirmPayload, db: Session = Depends(get_db)):
    return TradeService(db).confirm_trade(signal_id, payload.model_dump())


@router.post("/{signal_id}/ignore")
def ignore_signal(signal_id: int, db: Session = Depends(get_db)):
    return TradeService(db).ignore_signal(signal_id)


@router.post("/{signal_id}/false-positive")
def false_positive(signal_id: int, db: Session = Depends(get_db)):
    return TradeService(db).mark_false_positive(signal_id)
