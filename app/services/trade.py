from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import SignalRecord, TradeRecord


class TradeService:
    def __init__(self, db: Session):
        self.db = db

    def confirm_trade(self, signal_id: int, payload: dict) -> TradeRecord:
        signal = self.db.query(SignalRecord).filter(SignalRecord.id == signal_id).first()
        if not signal:
            raise ValueError("signal not found")
        existing = self.db.query(TradeRecord).filter(TradeRecord.signal_id == signal_id).first()
        if existing:
            raise ValueError("signal already confirmed")
        trade = TradeRecord(
            signal_id=signal_id,
            stock_code=signal.stock_code,
            stock_name=signal.stock_name,
            buy_price=payload["price"],
            quantity=payload["quantity"],
            position_ratio=payload["position"],
            stop_loss_price=payload.get("stop_loss_price"),
            target_price=payload.get("target_price"),
            trade_plan=payload.get("trade_plan", ""),
        )
        signal.handled_status = "confirmed"
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def ignore_signal(self, signal_id: int) -> SignalRecord:
        signal = self.db.query(SignalRecord).filter(SignalRecord.id == signal_id).first()
        if not signal:
            raise ValueError("signal not found")
        signal.handled_status = "ignored"
        self.db.commit()
        return signal

    def mark_false_positive(self, signal_id: int) -> SignalRecord:
        signal = self.db.query(SignalRecord).filter(SignalRecord.id == signal_id).first()
        if not signal:
            raise ValueError("signal not found")
        signal.handled_status = "false_positive"
        signal.valid = False
        self.db.commit()
        return signal

    def calculate_pnl(self, trade: TradeRecord) -> float | None:
        if trade.sell_price is None or trade.sell_quantity is None:
            return None
        return round((trade.sell_price - trade.buy_price) * trade.sell_quantity, 2)

    def sell_trade(self, trade_id: int, payload: dict) -> TradeRecord:
        trade = self.db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
        if not trade:
            raise ValueError("trade not found")
        trade.sell_price = payload["price"]
        trade.sell_quantity = payload["quantity"]
        trade.sell_reason = payload["reason"]
        trade.sell_time = datetime.utcnow()
        trade.status = "closed"
        trade.realized_pnl = self.calculate_pnl(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade
