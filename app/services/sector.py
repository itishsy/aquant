from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import SectorDaily
from app.providers.factory import ProviderFactory


class SectorService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = ProviderFactory.create()

    @staticmethod
    def calculate_sector_score(payload: dict) -> tuple[float, str, str, str]:
        score = round(
            payload["change_pct"] * 8
            + payload["limit_up_count"] * 4
            + payload["leader_board_count"] * 6
            + payload["fund_strength"] * 0.15
            + payload["continuity_days"] * 5
            + payload["heat_spread"] * 0.15,
            2,
        )
        if payload["continuity_days"] >= 3 and payload["change_pct"] > 2:
            sector_type = "主线板块"
        elif payload["change_pct"] > 1.5:
            sector_type = "轮动板块"
        elif payload["change_pct"] > 0:
            sector_type = "一日游板块"
        else:
            sector_type = "退潮板块"
        reason = f"涨幅{payload['change_pct']}%，涨停{payload['limit_up_count']}家，热度扩散{payload['heat_spread']}"
        risk = "注意持续性与分化风险" if sector_type != "退潮板块" else "板块退潮，禁止新入池"
        return score, sector_type, reason, risk

    def collect_sector_daily(self, trade_date: date) -> list[SectorDaily]:
        rows = []
        for payload in self.provider.get_sector_daily(trade_date):
            payload["trade_date"] = trade_date
            score, sector_type, reason, risk = self.calculate_sector_score(payload)
            entity = (
                self.db.query(SectorDaily)
                .filter(SectorDaily.trade_date == trade_date, SectorDaily.sector_name == payload["sector_name"])
                .first()
                or SectorDaily(trade_date=trade_date, sector_name=payload["sector_name"])
            )
            for key, value in payload.items():
                setattr(entity, key, value)
            entity.sector_score = score
            entity.sector_type = sector_type
            entity.reason = reason
            entity.risk_hint = risk
            self.db.add(entity)
            rows.append(entity)
        self.db.commit()
        return rows

    def get_top_sectors(self, trade_date: date, limit: int = 3) -> list[SectorDaily]:
        return (
            self.db.query(SectorDaily)
            .filter(SectorDaily.trade_date == trade_date)
            .order_by(SectorDaily.sector_score.desc())
            .limit(limit)
            .all()
        )
