from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.indicator import IndicatorService
from app.services.kline_collection import KlineFreshnessService
from app.services.kline_repository import KlineRepository


class TechnicalContextService:
    """Build a standardized technical-analysis context from unified K-line data."""

    def __init__(self, db: Session, repository: KlineRepository | None = None):
        self.db = db
        self.repository = repository or KlineRepository(db)

    def get_context(
        self,
        stock_code: str,
        timeframe: str,
        lookback_bars: int,
        indicators: list[str] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        indicators = self._normalize_indicators(indicators or [])
        required_bars = max(int(lookback_bars or 0), 0)
        bars = self.repository.get_recent_bars(stock_code, timeframe, required_bars) if required_bars else []
        latest_time = bars[-1].kline_time if bars else self.repository.latest_time(stock_code, timeframe)
        expected_time = KlineFreshnessService(self.repository).expected_latest_time(
            timeframe,
            now or datetime.now(ZoneInfo(get_settings().timezone)),
        )
        enough_bars = required_bars == 0 or len(bars) >= required_bars
        is_fresh = expected_time is None or (latest_time is not None and latest_time >= expected_time)
        status = "ok"
        reason = ""
        if latest_time is None:
            status = "missing_data"
            reason = f"No kline data for {stock_code} {timeframe}."
        elif not enough_bars:
            status = "insufficient_bars"
            reason = f"Need {required_bars} bars, got {len(bars)}."
        elif not is_fresh:
            status = "stale_data"
            reason = (
                f"Latest kline {latest_time.isoformat()} is older than expected "
                f"{expected_time.isoformat() if expected_time else ''}."
            )
        context = {
            "timeframe": timeframe,
            "bars": bars,
            "indicators": {},
            "freshness": {
                "latest_kline_time": latest_time.isoformat() if latest_time else None,
                "expected_latest_time": expected_time.isoformat() if expected_time else None,
                "bar_count": len(bars),
                "required_bars": required_bars,
                "enough_bars": enough_bars,
                "is_fresh": is_fresh,
            },
            "status": status,
            "reason": reason,
        }
        if status != "ok":
            return context

        closes = [float(row.close_price) for row in bars]
        if "macd" in indicators and closes:
            context["indicators"]["macd"] = IndicatorService.calculate_macd(closes)
        if "ma" in indicators and closes:
            context["indicators"]["ma"] = {
                "ma5": IndicatorService.calculate_ma(closes, 5),
                "ma10": IndicatorService.calculate_ma(closes, 10),
                "ma20": IndicatorService.calculate_ma(closes, 20),
            }
        return context

    @staticmethod
    def _normalize_indicators(indicators: list[str]) -> list[str]:
        result = []
        for item in indicators:
            value = str(item or "").strip().lower()
            if value and value not in result:
                result.append(value)
        return result
