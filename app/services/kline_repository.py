from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from sqlalchemy.orm import Session

from app.models import MktStockKline
from app.services.normalization import normalize_stock_code


class KlineRepository:
    """Unified repository for multi-timeframe stock K-line bars."""

    def __init__(self, db: Session):
        self.db = db

    def upsert_rows(self, stock_code: str, timeframe: str, rows: list[dict[str, Any]], source: str) -> int:
        stock_code = normalize_stock_code(stock_code)
        timeframe = self._normalize_timeframe(timeframe)
        source = source or "mock"
        affected = 0
        for payload in rows:
            kline_time = self._coerce_datetime(payload.get("kline_time") or payload.get("trade_time"))
            if kline_time is None and timeframe == "daily" and payload.get("trade_date"):
                kline_time = datetime.combine(self._coerce_date(payload["trade_date"]), time.min)
            if kline_time is None:
                raise ValueError("kline_time is required")
            trade_date = self._coerce_date(payload.get("trade_date") or kline_time.date())
            entity = (
                self.db.query(MktStockKline)
                .filter(
                    MktStockKline.stock_code == stock_code,
                    MktStockKline.timeframe == timeframe,
                    MktStockKline.kline_time == kline_time,
                    MktStockKline.source == source,
                )
                .first()
            )
            if entity is None:
                entity = MktStockKline(
                    stock_code=stock_code,
                    timeframe=timeframe,
                    kline_time=kline_time,
                    trade_date=trade_date,
                    source=source,
                )
            entity.open_price = self._required_float(payload, "open", "open_price")
            entity.high_price = self._required_float(payload, "high", "high_price")
            entity.low_price = self._required_float(payload, "low", "low_price")
            entity.close_price = self._required_float(payload, "close", "close_price")
            entity.volume = float(payload.get("volume", 0.0) or 0.0)
            entity.amount = float(payload.get("amount", 0.0) or 0.0)
            entity.source_update_time = self._coerce_datetime(payload.get("source_update_time"))
            self.db.add(entity)
            affected += 1
        self.db.commit()
        return affected

    def latest_time(self, stock_code: str, timeframe: str) -> datetime | None:
        row = (
            self.db.query(MktStockKline.kline_time)
            .filter(
                MktStockKline.stock_code == normalize_stock_code(stock_code),
                MktStockKline.timeframe == self._normalize_timeframe(timeframe),
            )
            .order_by(MktStockKline.kline_time.desc())
            .first()
        )
        return row[0] if row else None

    def get_recent_bars(self, stock_code: str, timeframe: str, limit: int) -> list[MktStockKline]:
        if limit <= 0:
            return []
        rows = (
            self.db.query(MktStockKline)
            .filter(
                MktStockKline.stock_code == normalize_stock_code(stock_code),
                MktStockKline.timeframe == self._normalize_timeframe(timeframe),
            )
            .order_by(MktStockKline.kline_time.desc())
            .limit(limit)
            .all()
        )
        return rows[::-1]

    def count_recent_bars(self, stock_code: str, timeframe: str, since: datetime | None = None) -> int:
        query = self.db.query(MktStockKline).filter(
            MktStockKline.stock_code == normalize_stock_code(stock_code),
            MktStockKline.timeframe == self._normalize_timeframe(timeframe),
        )
        if since is not None:
            query = query.filter(MktStockKline.kline_time >= since)
        return query.count()

    @staticmethod
    def _normalize_timeframe(timeframe: str) -> str:
        value = (timeframe or "").strip().lower()
        if value == "1d":
            return "daily"
        if value not in {"1m", "5m", "15m", "30m", "60m", "120m", "daily"}:
            raise ValueError(f"unsupported timeframe: {timeframe}")
        return value

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, time.min)
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        raise ValueError(f"invalid datetime value: {value!r}")

    @staticmethod
    def _coerce_date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value)
        raise ValueError(f"invalid date value: {value!r}")

    @staticmethod
    def _required_float(payload: dict[str, Any], *keys: str) -> float:
        for key in keys:
            if key in payload and payload[key] is not None:
                return float(payload[key])
        raise ValueError(f"{keys[0]} is required")
