from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.database import CandleSessionLocal
from app.models import StockKline15m, StockKlineDaily
from app.providers.factory import ProviderFactory
from app.services.quality import DataQualityService


class KlineService:
    def __init__(self, db: Session | None = None):
        self.db = db or CandleSessionLocal()
        self._owns_session = db is None
        self.provider = ProviderFactory.create()

    def close(self) -> None:
        if self._owns_session:
            self.db.close()

    def collect_daily_kline(self, stock_code: str, start_date: date, end_date: date) -> list[StockKlineDaily]:
        rows = []
        for payload in self.provider.get_daily_kline(stock_code, start_date, end_date):
            DataQualityService.validate_kline_daily(payload)
            existing = (
                self.db.query(StockKlineDaily)
                .filter(
                    StockKlineDaily.stock_code == stock_code,
                    StockKlineDaily.trade_date == payload["trade_date"],
                )
                .first()
            )
            entity = existing or StockKlineDaily(stock_code=stock_code, trade_date=payload["trade_date"])
            for key, value in payload.items():
                setattr(entity, key, value)
            self.db.add(entity)
            rows.append(entity)
        self.db.commit()
        return rows

    def collect_15m_kline(self, stock_code: str, start_time: datetime, end_time: datetime) -> list[StockKline15m]:
        rows = []
        for payload in self.provider.get_intraday_kline(stock_code, "15m", start_time, end_time):
            DataQualityService.validate_kline_15m(payload)
            existing = (
                self.db.query(StockKline15m)
                .filter(
                    StockKline15m.stock_code == stock_code,
                    StockKline15m.trade_time == payload["trade_time"],
                )
                .first()
            )
            entity = existing or StockKline15m(stock_code=stock_code, trade_time=payload["trade_time"])
            for key, value in payload.items():
                if key != "mock_macd_hint":
                    setattr(entity, key, value)
            self.db.add(entity)
            rows.append(entity)
        self.db.commit()
        return rows

    def get_daily_kline(self, stock_code: str, limit: int = 100) -> list[StockKlineDaily]:
        if not self.db.query(StockKlineDaily).filter(StockKlineDaily.stock_code == stock_code).first():
            today = date.today()
            self.collect_daily_kline(stock_code, today - timedelta(days=limit), today)
        return (
            self.db.query(StockKlineDaily)
            .filter(StockKlineDaily.stock_code == stock_code)
            .order_by(StockKlineDaily.trade_date.desc())
            .limit(limit)
            .all()[::-1]
        )

    def get_15m_kline(self, stock_code: str, limit: int = 200) -> list[StockKline15m]:
        if not self.db.query(StockKline15m).filter(StockKline15m.stock_code == stock_code).first():
            session_day = datetime.utcnow().date()
            start_time = datetime.combine(session_day, time(9, 30))
            end_time = datetime.combine(session_day, time(15, 0))
            self.collect_15m_kline(stock_code, start_time, end_time)
        return (
            self.db.query(StockKline15m)
            .filter(StockKline15m.stock_code == stock_code)
            .order_by(StockKline15m.trade_time.desc())
            .limit(limit)
            .all()[::-1]
        )

    def __del__(self) -> None:
        self.close()
