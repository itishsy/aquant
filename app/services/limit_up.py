from __future__ import annotations

from collections import Counter
from datetime import date

from sqlalchemy.orm import Session

from app.models import LimitUpDaily
from app.providers.factory import ProviderFactory


class LimitUpService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = ProviderFactory.create()

    @staticmethod
    def classify_limit_up_stock(item: dict) -> str:
        if item["open_limit_count"] > 0:
            return "炸板回封"
        if item["board_count"] >= 3:
            return "三板及以上"
        if item["board_count"] == 2:
            return "二板涨停"
        return "首板涨停"

    def collect_limit_up_daily(self, trade_date: date) -> list[LimitUpDaily]:
        rows = []
        self.db.query(LimitUpDaily).filter(LimitUpDaily.trade_date == trade_date).delete()
        for payload in self.provider.get_limit_up_list(trade_date):
            payload["trade_date"] = trade_date
            payload["limit_type"] = self.classify_limit_up_stock(payload)
            entity = LimitUpDaily(**payload)
            self.db.add(entity)
            rows.append(entity)
        self.db.commit()
        return rows

    def generate_limit_up_summary(self, trade_date: date) -> dict:
        rows = self.db.query(LimitUpDaily).filter(LimitUpDaily.trade_date == trade_date).all()
        concepts = Counter(row.concept for row in rows)
        broken_rate = round(sum(1 for row in rows if row.open_limit_count > 0) / len(rows), 2) if rows else 0
        return {
            "trade_date": trade_date,
            "count": len(rows),
            "max_continue_board": max((row.board_count for row in rows), default=0),
            "first_board_count": sum(1 for row in rows if row.is_first_board),
            "continue_board_count": sum(1 for row in rows if row.is_continue_board),
            "broken_limit_rate": broken_rate,
            "concept_distribution": dict(concepts),
        }
