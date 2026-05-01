from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import MarketReviewDaily
from app.providers.factory import ProviderFactory


class MarketReviewService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = ProviderFactory.create()

    def collect_market_review(self, trade_date: date) -> MarketReviewDaily:
        if not hasattr(self.provider, "get_market_review_snapshot"):
            payload = self._empty_payload(trade_date)
        else:
            payload = self.provider.get_market_review_snapshot(trade_date)
        payload["trade_date"] = trade_date
        existing = self.db.query(MarketReviewDaily).filter(MarketReviewDaily.trade_date == trade_date).first()
        target = existing or MarketReviewDaily(trade_date=trade_date)
        for key, value in payload.items():
            setattr(target, key, value)
        self.db.add(target)
        self.db.commit()
        self.db.refresh(target)
        return target

    def get_market_review(self, trade_date: date) -> MarketReviewDaily | None:
        return self.db.query(MarketReviewDaily).filter(MarketReviewDaily.trade_date == trade_date).first()

    @staticmethod
    def _empty_payload(trade_date: date) -> dict:
        return {
            "trade_date": trade_date,
            "review_text": "",
            "concept": "",
            "chance": [],
            "tuyere": [],
            "topic": [],
            "subject": [],
            "fund": {},
            "latent": [],
            "raw_snapshot": {"provider": "empty"},
        }
