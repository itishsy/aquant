from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.indicator import IndicatorService
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
    ) -> dict[str, Any]:
        indicators = self._normalize_indicators(indicators or [])
        required_bars = max(int(lookback_bars or 0), 0)
        bars = self.repository.get_recent_bars(stock_code, timeframe, required_bars) if required_bars else []
        latest_time = bars[-1].kline_time if bars else self.repository.latest_time(stock_code, timeframe)
        enough_bars = required_bars == 0 or len(bars) >= required_bars
        context = {
            "timeframe": timeframe,
            "bars": bars,
            "indicators": {},
            "freshness": {
                "latest_kline_time": latest_time.isoformat() if latest_time else None,
                "bar_count": len(bars),
                "required_bars": required_bars,
                "enough_bars": enough_bars,
            },
            "status": "ok" if enough_bars else "insufficient_bars",
            "reason": "" if enough_bars else f"Need {required_bars} bars, got {len(bars)}.",
        }
        if not enough_bars:
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
