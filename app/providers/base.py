from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime


class MarketDataProvider(ABC):
    @abstractmethod
    def get_market_snapshot(self, trade_date: date) -> dict: ...

    @abstractmethod
    def get_daily_kline(self, stock_code: str, start_date: date, end_date: date) -> list[dict]: ...

    @abstractmethod
    def get_intraday_kline(
        self, stock_code: str, interval: str, start_time: datetime, end_time: datetime
    ) -> list[dict]: ...


class HotRankProvider(ABC):
    @abstractmethod
    def get_hot_stock_rank(self, trade_date: date) -> list[dict]: ...


class LimitUpProvider(ABC):
    @abstractmethod
    def get_limit_up_list(self, trade_date: date) -> list[dict]: ...


class SectorDataProvider(ABC):
    @abstractmethod
    def get_sector_daily(self, trade_date: date) -> list[dict]: ...


class TradingCalendarProvider(ABC):
    @abstractmethod
    def is_trade_day(self, day: date) -> bool: ...

    @abstractmethod
    def previous_trade_day(self, day: date) -> date: ...
