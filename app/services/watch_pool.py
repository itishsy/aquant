from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import SectorDaily, SignalRecord, WatchPool
from app.services.hot_stock import HotStockService
from app.services.normalization import normalize_stock_code


class WatchPoolService:
    def __init__(self, db: Session):
        self.db = db

    def list_watch_pool(self, filters: dict | None = None) -> list[WatchPool]:
        query = self.db.query(WatchPool).filter(WatchPool.active.is_(True))
        if filters and filters.get("label"):
            query = query.filter(WatchPool.labels.like(f"%{filters['label']}%"))
        return query.order_by(WatchPool.created_at.desc()).all()

    def add_to_watch_pool(
        self, stock_code: str, reason: str, labels: list[str], strategy_type: str
    ) -> WatchPool:
        stock_code = normalize_stock_code(stock_code)
        existing = self.db.query(WatchPool).filter(WatchPool.stock_code == stock_code).first()
        if existing:
            existing.active = True
            existing.reason = reason
            existing.labels = labels
            existing.strategy_type = strategy_type
            self.db.commit()
            return existing
        entity = WatchPool(
            stock_code=stock_code,
            stock_name=stock_code,
            reason=reason,
            labels=labels,
            strategy_type=strategy_type,
            added_trade_date=date.today(),
        )
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def remove_from_watch_pool(self, stock_code: str, reason: str) -> None:
        stock_code = normalize_stock_code(stock_code)
        entity = self.db.query(WatchPool).filter(WatchPool.stock_code == stock_code).first()
        if entity:
            entity.active = False
            entity.reason = f"{entity.reason} | removed:{reason}"
            self.db.commit()

    def update_labels(self, stock_code: str, labels: list[str]) -> WatchPool:
        stock_code = normalize_stock_code(stock_code)
        entity = self.db.query(WatchPool).filter(WatchPool.stock_code == stock_code).first()
        if not entity:
            raise ValueError("watch pool stock not found")
        entity.labels = labels
        self.db.commit()
        return entity

    def mark_blacklist(self, stock_code: str, reason: str) -> WatchPool:
        stock_code = normalize_stock_code(stock_code)
        entity = self.db.query(WatchPool).filter(WatchPool.stock_code == stock_code).first()
        if not entity:
            entity = WatchPool(stock_code=stock_code, stock_name=stock_code, reason="blacklist")
            self.db.add(entity)
        entity.is_blacklist = True
        entity.blacklist_reason = reason
        entity.active = False
        self.db.commit()
        return entity

    def auto_add_candidates(self, trade_date: date) -> list[WatchPool]:
        # Deprecated by latest PRD v1.0: every watch-pool item must be added by
        # explicit user confirmation. Keep the method as a safe no-op for old
        # callers and scheduled-task compatibility.
        return []

    def auto_remove_invalid(self, trade_date: date) -> int:
        removed = 0
        records = self.db.query(WatchPool).filter(WatchPool.active.is_(True)).all()
        for row in records:
            if row.added_trade_date and row.added_trade_date < trade_date - timedelta(days=40):
                has_recent_signal = (
                    self.db.query(SignalRecord)
                    .filter(SignalRecord.stock_code == row.stock_code, SignalRecord.valid.is_(True))
                    .first()
                )
                if not has_recent_signal:
                    row.active = False
                    removed += 1
        self.db.commit()
        return removed
