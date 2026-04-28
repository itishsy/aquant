from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.models import HotStockRank, LimitUpDaily, SectorDaily
from app.providers.mock_provider import MockProvider
from app.providers.factory import ProviderFactory


class HotStockService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = ProviderFactory.create()

    def collect_hot_stock_rank(self, trade_date: date) -> list[HotStockRank]:
        items = self.provider.get_hot_stock_rank(trade_date)
        aggregated = self.calculate_hot_score(items, trade_date)
        saved: list[HotStockRank] = []
        self.db.query(HotStockRank).filter(HotStockRank.trade_date == trade_date).delete()
        for item in aggregated:
            entity = HotStockRank(**item)
            self.db.add(entity)
            saved.append(entity)
        self.db.commit()
        return saved

    def calculate_hot_score(self, raw_rank_items: list[dict], trade_date: date) -> list[dict]:
        grouped: dict[str, dict] = defaultdict(lambda: {"platforms": {}, "base": None})
        main_sectors = {
            row.sector_name
            for row in self.db.query(SectorDaily)
            .filter(SectorDaily.trade_date == trade_date, SectorDaily.sector_type == "主线板块")
            .all()
        }
        limit_up_codes = {
            row.stock_code for row in self.db.query(LimitUpDaily).filter(LimitUpDaily.trade_date == trade_date).all()
        }
        for row in raw_rank_items:
            grouped[row["stock_code"]]["base"] = row
            grouped[row["stock_code"]]["platforms"][row["platform"]] = row["platform_rank"]

        result = []
        for stock_code, meta in grouped.items():
            base = meta["base"]
            platforms = meta["platforms"]
            score = sum(MockProvider.PRIME_SCORES[rank] for rank in platforms.values())
            resonance = 15 if len(platforms) >= 3 else 8 if len(platforms) == 2 else 0
            if base["sector_name"] in main_sectors:
                resonance += 10
            is_limit_up = stock_code in limit_up_codes
            if is_limit_up:
                resonance += 8
            is_continue = any(code == stock_code and row.board_count >= 2 for code, row in [(x.stock_code, x) for x in self.db.query(LimitUpDaily).filter(LimitUpDaily.trade_date == trade_date).all()])
            if is_continue:
                resonance += 10
            total = score + resonance
            for platform, rank in platforms.items():
                result.append(
                    {
                        "trade_date": trade_date,
                        "stock_code": stock_code,
                        "stock_name": base["stock_name"],
                        "sector_name": base["sector_name"],
                        "platform": platform,
                        "platform_rank": rank,
                        "rank_score": MockProvider.PRIME_SCORES[rank],
                        "resonance_score": resonance,
                        "total_score": total,
                        "is_limit_up": is_limit_up,
                        "is_continue_board": is_continue,
                        "raw_payload": {"platforms": platforms},
                    }
                )
        return result

    def get_top_hot_stocks(self, trade_date: date, limit: int = 10) -> list[dict]:
        rows = self.db.query(HotStockRank).filter(HotStockRank.trade_date == trade_date).all()
        grouped: dict[str, dict] = {}
        for row in rows:
            if row.stock_code not in grouped:
                grouped[row.stock_code] = {
                    "stock_code": row.stock_code,
                    "stock_name": row.stock_name,
                    "sector_name": row.sector_name,
                    "platform_ranks": {},
                    "total_score": row.total_score,
                }
            grouped[row.stock_code]["platform_ranks"][row.platform] = row.platform_rank
            grouped[row.stock_code]["total_score"] = max(grouped[row.stock_code]["total_score"], row.total_score)
        return sorted(grouped.values(), key=lambda item: item["total_score"], reverse=True)[:limit]
