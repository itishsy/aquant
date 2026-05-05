from __future__ import annotations

from app.services.indicator import IndicatorService
from app.strategies.base import StrategyBase


def _value(row: object, attr: str) -> float:
    return float(getattr(row, attr))


class HighVolumeRiskStrategy(StrategyBase):
    name = "high_volume_risk"
    type = "risk"

    def validate_preconditions(self, context: dict) -> bool:
        return context.get("data_quality_ok", True)

    def generate_signal(self, context: dict) -> dict | None:
        bars = context["kline_daily"]
        if len(bars) < 20:
            return None
        closes = [_value(row, "close_price") for row in bars]
        highs = [_value(row, "high_price") for row in bars]
        lows = [_value(row, "low_price") for row in bars]
        volumes = [_value(row, "volume") for row in bars]
        ma20 = IndicatorService.calculate_ma(closes, 20)
        if ma20[-1] is None:
            return None
        at_high_area = closes[-1] >= max(closes[-20:]) * 0.97
        volume_spike = volumes[-1] >= sum(volumes[-5:]) / 5 * 1.6
        upper_shadow = highs[-1] - closes[-1] > (highs[-1] - lows[-1]) * 0.45
        weak_close = closes[-1] <= closes[-2] * 1.01
        if not all([at_high_area, volume_spike, upper_shadow, weak_close]):
            return None
        return {
            "signal_type": "risk",
            "signal_text": "风险提醒",
            "strategy_name": self.name,
            "signal_level": "A",
            "trigger_price": closes[-1],
            "trigger_reason": "高位区域出现明显放量和长上影，需关注冲高回落风险。",
            "risk_desc": "若后续无法继续走强，应优先按个人交易规则处理风险。",
            "raw_snapshot": {"closes": closes[-20:], "volumes": volumes[-5:]},
        }


class BreakoutFailureStrategy(StrategyBase):
    name = "breakout_failure"
    type = "sell"

    def validate_preconditions(self, context: dict) -> bool:
        return context.get("data_quality_ok", True)

    def generate_signal(self, context: dict) -> dict | None:
        bars = context["kline_daily"]
        if len(bars) < 10:
            return None
        closes = [_value(row, "close_price") for row in bars]
        highs = [_value(row, "high_price") for row in bars]
        volumes = [_value(row, "volume") for row in bars]
        pressure = max(highs[-10:-1])
        breakout_failed = highs[-1] > pressure and closes[-1] < pressure
        volume_spike = volumes[-1] > sum(volumes[-5:]) / 5 * 1.3
        if not (breakout_failed and volume_spike):
            return None
        return {
            "signal_type": "sell",
            "signal_text": "卖出观察提醒",
            "strategy_name": self.name,
            "signal_level": "B",
            "trigger_price": closes[-1],
            "trigger_reason": "突破压力位后快速回落，收盘未站稳压力位。",
            "risk_desc": "若继续跌破突破平台，应优先关注风险控制。",
            "raw_snapshot": {"pressure": pressure, "close": closes[-1], "high": highs[-1], "volume": volumes[-1]},
        }
