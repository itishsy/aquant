from __future__ import annotations

from app.services.indicator import IndicatorService
from app.strategies.base import StrategyBase


class Macd15BullishDivergenceStrategy(StrategyBase):
    name = "macd_15m_bullish_divergence"
    type = "buy"

    def validate_preconditions(self, context: dict) -> bool:
        return (
            context.get("in_watch_pool", False)
            and context.get("market_status") not in {"退潮", "冰点"}
            and context.get("sector_type") != "退潮板块"
            and not context.get("high_volume_distribution", False)
            and not context.get("daily_trend_broken", False)
            and context.get("data_quality_ok", True)
        )

    def generate_signal(self, context: dict) -> dict | None:
        bars = context["kline_15m"]
        closes = [row.close for row in bars]
        volumes = [row.volume for row in bars]
        macd = IndicatorService.calculate_macd(closes)
        if len(closes) < 6:
            return None
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
            "trigger_reason": "15分钟价格接近新低但MACD未同步新低，存在底背离并接近金叉，仅作为交易辅助",
            "risk_desc": "若后续跌破支撑位或市场转入退潮/冰点，需重新评估，仅作为交易辅助",
            "invalid_condition": "跌破参考止损位或板块转入退潮，仅作为交易辅助",
            "stop_loss_price": round(min(closes[-4:]) * 0.98, 2),
            "raw_snapshot": {
                "closes": closes,
                "volumes": volumes,
                "macd": macd,
                "market_status": context["market_status"],
                "sector_name": context.get("sector_name"),
                "sector_type": context.get("sector_type"),
            },
        }
