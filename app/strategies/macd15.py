from __future__ import annotations

from app.services.indicator import IndicatorService
from app.strategies.base import StrategyBase


def _value(row: object, attr: str) -> float:
    return float(getattr(row, attr))


class Macd15BullishDivergenceStrategy(StrategyBase):
    name = "macd_15m_bullish_divergence"
    type = "buy"

    def validate_preconditions(self, context: dict) -> bool:
        return (
            context.get("in_watch_pool", False)
            and context.get("monitor_enabled", False)
            and context.get("pool_status") == "观察中"
            and context.get("data_quality_ok", True)
        )

    def generate_signal(self, context: dict) -> dict | None:
        bars = context["kline_15m"]
        if len(bars) < 8:
            return None
        closes = [_value(row, "close_price") for row in bars]
        volumes = [_value(row, "volume") for row in bars]
        macd = IndicatorService.calculate_macd(closes)
        recent_window = closes[-8:]
        prior_low = min(recent_window[:4])
        recent_low = min(recent_window[4:])
        price_lower = recent_low <= prior_low * 1.01 and closes[-1] > recent_low
        recent_hist = macd["hist"][-6:]
        macd_higher = min(recent_hist[3:]) > min(recent_hist[:3])
        dif_turning = macd["dif"][-1] > macd["dif"][-2] > macd["dif"][-3]
        golden_cross_near = macd["dif"][-1] >= macd["dea"][-1] or abs(macd["dif"][-1] - macd["dea"][-1]) < 0.08
        volume_ok = min(volumes[-3:]) <= max(volumes[-6:-3]) and volumes[-1] >= volumes[-2] * 0.9
        near_support = closes[-1] <= min(closes[-6:]) * 1.03 or closes[-2] <= min(closes[-6:]) * 1.02
        if not all([price_lower, macd_higher, dif_turning, golden_cross_near, volume_ok, near_support]):
            return None
        return {
            "signal_type": "buy",
            "signal_text": "买入观察信号",
            "strategy_name": self.name,
            "signal_level": "A",
            "trigger_price": closes[-1],
            "trigger_reason": "15 分钟价格接近新低但 MACD 未同步新低，出现底背离观察条件。",
            "risk_desc": "若跌破参考支撑或数据不完整，应重新评估。",
            "raw_snapshot": {
                "closes": closes,
                "volumes": volumes,
                "macd": macd,
                "stock_code": context["stock_code"],
                "watch_id": context["watch_id"],
            },
        }
