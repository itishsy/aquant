from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.database import SystemSessionLocal
from app.models import MktStockKline15m, MktStockKlineDaily
from app.providers.factory import ProviderFactory
from app.services.normalization import normalize_stock_code
from app.services.quality import DataQualityService


class KlineService:
    """Backend-only K-line collection and lookup for strategies/reviews."""

    def __init__(self, db: Session | None = None):
        self.db = db or SystemSessionLocal()
        self._owns_session = db is None
        self.provider = ProviderFactory.create()

    def close(self) -> None:
        if self._owns_session:
            self.db.close()

    def collect_daily_kline(self, stock_code: str, start_date: date, end_date: date) -> list[MktStockKlineDaily]:
        stock_code = normalize_stock_code(stock_code)
        rows: list[MktStockKlineDaily] = []
        for payload in self.provider.get_daily_kline(stock_code, start_date, end_date):
            DataQualityService.validate_kline_daily(payload)
            trade_date = payload["trade_date"]
            source = payload.get("source", "mock")
            entity = (
                self.db.query(MktStockKlineDaily)
                .filter(
                    MktStockKlineDaily.stock_code == stock_code,
                    MktStockKlineDaily.trade_date == trade_date,
                    MktStockKlineDaily.source == source,
                )
                .first()
            ) or MktStockKlineDaily(stock_code=stock_code, trade_date=trade_date, source=source)
            entity.open_price = payload["open"]
            entity.high_price = payload["high"]
            entity.low_price = payload["low"]
            entity.close_price = payload["close"]
            entity.volume = payload.get("volume", 0.0)
            entity.amount = payload.get("amount", 0.0)
            entity.ma5 = payload.get("ma5")
            entity.ma10 = payload.get("ma10")
            entity.ma20 = payload.get("ma20")
            entity.source_update_time = payload.get("source_update_time")
            self.db.add(entity)
            rows.append(entity)
        self.db.commit()
        return rows

    def collect_15m_kline(self, stock_code: str, start_time: datetime, end_time: datetime) -> list[MktStockKline15m]:
        rows: list[MktStockKline15m] = []
        for payload in self.provider.get_intraday_kline(stock_code, "15m", start_time, end_time):
            DataQualityService.validate_kline_15m(payload)
            kline_time = payload.get("kline_time") or payload["trade_time"]
            source = payload.get("source", "mock")
            entity = (
                self.db.query(MktStockKline15m)
                .filter(
                    MktStockKline15m.stock_code == stock_code,
                    MktStockKline15m.kline_time == kline_time,
                    MktStockKline15m.source == source,
                )
                .first()
            ) or MktStockKline15m(stock_code=stock_code, kline_time=kline_time, source=source)
            entity.open_price = payload["open"]
            entity.high_price = payload["high"]
            entity.low_price = payload["low"]
            entity.close_price = payload["close"]
            entity.volume = payload.get("volume", 0.0)
            entity.amount = payload.get("amount", 0.0)
            entity.source_update_time = payload.get("source_update_time")
            self.db.add(entity)
            rows.append(entity)
        self.db.commit()
        return rows

    def get_daily_kline(self, stock_code: str, limit: int = 100) -> list[MktStockKlineDaily]:
        stock_code = normalize_stock_code(stock_code)
        today = date.today()
        cls_query = self.db.query(MktStockKlineDaily).filter(
            MktStockKlineDaily.stock_code == stock_code,
            MktStockKlineDaily.source == "cls",
        )
        newest = (
            self.db.query(MktStockKlineDaily)
            .filter(MktStockKlineDaily.stock_code == stock_code)
            .order_by(MktStockKlineDaily.trade_date.desc())
            .first()
        )
        if not newest:
            self.collect_daily_kline(stock_code, today - timedelta(days=limit * 2), today)
        elif newest.trade_date and newest.trade_date < today:
            self.collect_daily_kline(stock_code, newest.trade_date + timedelta(days=1), today)
        return (
            self.db.query(MktStockKlineDaily)
            .filter(MktStockKlineDaily.stock_code == stock_code)
            .order_by(MktStockKlineDaily.trade_date.desc())
            .limit(limit)
            .all()[::-1]
        )

    def get_15m_kline(self, stock_code: str, limit: int = 200) -> list[MktStockKline15m]:
        newest = (
            self.db.query(MktStockKline15m)
            .filter(MktStockKline15m.stock_code == stock_code)
            .order_by(MktStockKline15m.kline_time.desc())
            .first()
        )
        session_day = datetime.utcnow().date()
        if not newest:
            start_time = datetime.combine(session_day, time(9, 30))
            end_time = datetime.combine(session_day, time(15, 0))
            self.collect_15m_kline(stock_code, start_time, end_time)
        elif newest.kline_time and newest.kline_time.date() < session_day:
            start_time = datetime.combine(newest.kline_time.date(), time(9, 30)) + timedelta(days=1)
            end_time = datetime.combine(session_day, time(15, 0))
            self.collect_15m_kline(stock_code, start_time, end_time)
        return (
            self.db.query(MktStockKline15m)
            .filter(MktStockKline15m.stock_code == stock_code)
            .order_by(MktStockKline15m.kline_time.desc())
            .limit(limit)
            .all()[::-1]
        )

    def __del__(self) -> None:
        self.close()
