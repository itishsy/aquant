from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import TradeRecord
from app.schemas.common import ReviewPayload, TradeOut, TradeSellPayload
from app.services.review import ReviewService
from app.services.trade import TradeService

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=list[TradeOut])
def list_trades(db: Session = Depends(get_db)):
    return db.query(TradeRecord).order_by(TradeRecord.created_at.desc()).all()


@router.get("/{trade_id}", response_model=TradeOut | None)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    return db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()


@router.post("/{trade_id}/sell", response_model=TradeOut)
def sell_trade(trade_id: int, payload: TradeSellPayload, db: Session = Depends(get_db)):
    return TradeService(db).sell_trade(trade_id, payload.model_dump())


@router.post("/{trade_id}/review")
def review_trade(trade_id: int, payload: ReviewPayload, db: Session = Depends(get_db)):
    review = ReviewService(db).generate_trade_review(trade_id)
    review.user_notes = payload.user_notes
    review.failure_reason = payload.failure_reason
    db.commit()
    return review
