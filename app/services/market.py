from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import MarketDaily
from app.providers.factory import ProviderFactory


class MarketService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = ProviderFactory.create()

    @staticmethod
    def calculate_market_score(payload: dict) -> tuple[float, str]:
        index_score = min(max((payload["sh_index"] - 3000) / 4.0, 0), 100)
        breadth_score = min(max(payload["up_ratio"] * 100, 0), 100)
        emotion_score = min(payload["limit_up_count"] * 1.2 + payload["max_continue_board"] * 4, 100)
        risk_score = max(100 - payload["limit_down_count"] * 10 - payload["broken_limit_ratio"] * 100, 0)
        amount_score = min(payload["total_amount"] / 150, 100)
        score = round(
            index_score * 0.2
            + breadth_score * 0.2
            + emotion_score * 0.2
            + risk_score * 0.2
            + amount_score * 0.2,
            2,
        )
        if score >= 80:
            status = "强势"
        elif score >= 65:
            status = "修复"
        elif score >= 50:
            status = "震荡"
        elif score >= 30:
            status = "退潮"
        else:
            status = "冰点"
        return score, status

    def collect_market_daily(self, trade_date: date) -> MarketDaily:
        payload = self.provider.get_market_snapshot(trade_date)
        score, status = self.calculate_market_score(payload)
        existing = self.db.query(MarketDaily).filter(MarketDaily.trade_date == trade_date).first()
        target = existing or MarketDaily(trade_date=trade_date)
        for key, value in payload.items():
            setattr(target, key, value)
        target.market_score = score
        target.market_status = status
        self.db.add(target)
        self.db.commit()
        self.db.refresh(target)
        return target

    def get_market_daily(self, trade_date: date) -> MarketDaily | None:
        return self.db.query(MarketDaily).filter(MarketDaily.trade_date == trade_date).first()

    def get_market_summary(self) -> dict:
        latest = self.db.query(MarketDaily).order_by(MarketDaily.trade_date.desc()).first()
        if not latest:
            raise ValueError("market data not found")
        return {
            "trade_date": latest.trade_date,
            "market_score": latest.market_score,
            "market_status": latest.market_status,
            "market_comment": latest.market_comment,
            "total_amount": latest.total_amount,
            "up_ratio": latest.up_ratio,
            "limit_up_count": latest.limit_up_count,
            "limit_down_count": latest.limit_down_count,
            "max_continue_board": latest.max_continue_board,
        }
