from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.providers.factory import ProviderFactory
from app.services.kline_repository import KlineRepository
from app.services.rule_data_requirements import RequirementMap, RuleDataRequirementService


class KlineFreshnessService:
    """Determine whether local unified K-line data is fresh enough to skip collection."""

    SUPPORTED_TIMEFRAMES = {"daily", "1m", "5m", "15m", "30m", "60m", "120m"}

    def __init__(self, repository: KlineRepository):
        self.repository = repository

    def expected_latest_time(self, timeframe: str, now: datetime) -> datetime | None:
        now = self._as_exchange_naive(now)
        timeframe = self._normalize_timeframe(timeframe)
        if timeframe == "daily":
            return datetime.combine(now.date(), time.min) if now.time() >= time(15, 0) else None
        minutes = self._minutes(timeframe)
        if not self._in_continuous_trading_session(now.time()):
            return None
        session_start = datetime.combine(now.date(), time(9, 30))
        elapsed = int((now - session_start).total_seconds() // 60)
        completed = elapsed - (elapsed % minutes)
        if elapsed == completed:
            completed -= minutes
        if completed <= 0:
            return None
        return session_start + timedelta(minutes=completed)

    def is_fresh(self, stock_code: str, timeframe: str, now: datetime) -> bool:
        expected = self.expected_latest_time(timeframe, now)
        if expected is None:
            return True
        latest = self.repository.latest_time(stock_code, timeframe)
        return latest is not None and latest >= expected

    def missing_window(self, stock_code: str, timeframe: str, now: datetime) -> tuple[datetime, datetime] | None:
        expected = self.expected_latest_time(timeframe, now)
        if expected is None:
            return None
        latest = self.repository.latest_time(stock_code, timeframe)
        if latest is not None and latest >= expected:
            return None
        if self._normalize_timeframe(timeframe) == "daily":
            start = latest + timedelta(days=1) if latest else expected
        else:
            start = latest + timedelta(minutes=self._minutes(timeframe)) if latest else datetime.combine(expected.date(), time(9, 30))
        if start > expected:
            return None
        return start, expected

    @staticmethod
    def _normalize_timeframe(timeframe: str) -> str:
        value = (timeframe or "").strip().lower()
        return "daily" if value == "1d" else value

    @classmethod
    def _minutes(cls, timeframe: str) -> int:
        if timeframe not in cls.SUPPORTED_TIMEFRAMES or timeframe == "daily":
            raise ValueError(f"unsupported timeframe: {timeframe}")
        return int(timeframe[:-1])

    @staticmethod
    def _in_continuous_trading_session(value: time) -> bool:
        return time(9, 30) < value <= time(11, 30) or time(13, 0) < value <= time(15, 0)

    @staticmethod
    def _as_exchange_naive(value: datetime) -> datetime:
        """Interpret aware datetimes in the configured market timezone, stored as local-naive."""
        if value.tzinfo is None:
            return value
        return value.astimezone(ZoneInfo(get_settings().timezone)).replace(tzinfo=None)


class KlineCollectionService:
    """Collect only the multi-timeframe K-line data required by trading-system rules."""

    def __init__(
        self,
        db: Session,
        provider: Any | None = None,
        repository: KlineRepository | None = None,
        now: datetime | None = None,
        max_requests_per_run: int = 100,
        max_stocks_per_run: int | None = None,
        timeframes: list[str] | None = None,
    ):
        self.db = db
        self.provider = provider or ProviderFactory.create()
        self.repository = repository or KlineRepository(db)
        self.freshness = KlineFreshnessService(self.repository)
        self.now = now
        self.max_requests_per_run = max_requests_per_run
        self.max_stocks_per_run = max_stocks_per_run
        self.timeframes = {KlineFreshnessService._normalize_timeframe(item) for item in timeframes or []}
        self.errors: list[str] = []

    def collect_for_requirements(self, requirements: RequirementMap) -> int:
        self.errors = []
        affected = 0
        requests = 0
        now = self.now or datetime.now(ZoneInfo(get_settings().timezone))
        for stock_index, (stock_code, timeframe_map) in enumerate(requirements.items(), start=1):
            if self.max_stocks_per_run and stock_index > self.max_stocks_per_run:
                self.errors.append("max_stocks_per_run reached")
                return affected
            for timeframe, requirement in timeframe_map.items():
                if self.timeframes and KlineFreshnessService._normalize_timeframe(timeframe) not in self.timeframes:
                    continue
                if requests >= self.max_requests_per_run:
                    self.errors.append("max_requests_per_run reached")
                    return affected
                window = self.freshness.missing_window(stock_code, timeframe, now)
                if window is None:
                    continue
                requests += 1
                try:
                    affected += self._collect_window(stock_code, timeframe, requirement, window)
                except Exception as exc:  # noqa: BLE001 - collection should continue across symbols.
                    self.db.rollback()
                    self.errors.append(f"{stock_code} {timeframe}: {exc}")
        return affected

    def prepare_watch_rule_data(self, trade_date: date) -> int:
        requirements = RuleDataRequirementService(self.db).build_watch_requirements(trade_date)
        return self.collect_for_requirements(requirements)

    def prepare_trade_rule_data(self, trade_date: date) -> int:
        requirements = RuleDataRequirementService(self.db).build_trade_requirements(trade_date)
        return self.collect_for_requirements(requirements)

    def error_summary(self) -> str:
        return "; ".join(self.errors[:5])

    def _collect_window(
        self,
        stock_code: str,
        timeframe: str,
        requirement: dict[str, Any],
        window: tuple[datetime, datetime],
    ) -> int:
        timeframe = KlineFreshnessService._normalize_timeframe(timeframe)
        start_time, end_time = window
        lookback = int(requirement.get("lookback_bars") or 0)
        if timeframe == "daily":
            start_date = start_time.date()
            if lookback and start_time == end_time:
                start_date = start_date - timedelta(days=lookback * 2)
            rows = self.provider.get_daily_kline(stock_code, start_date, end_time.date())
        else:
            rows = self.provider.get_intraday_kline(stock_code, timeframe, start_time, end_time)
        return self._upsert_grouped_by_source(stock_code, timeframe, rows)

    def _upsert_grouped_by_source(self, stock_code: str, timeframe: str, rows: list[dict]) -> int:
        grouped: dict[str, list[dict]] = {}
        for row in rows or []:
            grouped.setdefault(row.get("source") or "mock", []).append(row)
        affected = 0
        for source, source_rows in grouped.items():
            affected += self.repository.upsert_rows(stock_code, timeframe, source_rows, source)
        return affected
