from __future__ import annotations

from app.services.indicator import IndicatorService
from app.strategies.base import StrategyBase


class HighVolumeRiskStrategy(StrategyBase):
    name = "high_volume_risk"
    type = "risk"

    def validate_preconditions(self, context: dict) -> bool:
        return context.get("data_quality_ok", True)

    def generate_signal(self, context: dict) -> dict | None:
        bars = context["kline_daily"]
        closes = [row.close for row in bars]
        highs = [row.high for row in bars]
        volumes = [row.volume for row in bars]
        ma20 = IndicatorService.calculate_ma(closes, 20)
        if len(closes) < 20 or ma20[-1] is None:
            return None
        at_high_area = closes[-1] >= max(closes[-20:]) * 0.97
        volume_spike = volumes[-1] >= sum(volumes[-5:]) / 5 * 1.6
        upper_shadow = highs[-1] - closes[-1] > (highs[-1] - bars[-1].low) * 0.45
        weak_close = closes[-1] <= closes[-2] * 1.01
        if not all([at_high_area, volume_spike, upper_shadow, weak_close]):
            return None
        return {
            "signal_type": "risk",
            "signal_text": "风险提醒",
            "strategy_name": self.name,
            "signal_level": "A",
            "trigger_reason": "高位区域放量且长上影，存在冲高回落风险，仅作为交易辅助",
            "risk_desc": "若次日无法继续走强，应继续观察减仓/退出节奏，仅作为交易辅助",
            "invalid_condition": "次日放量反包并重新站稳高点，仅作为交易辅助",
            "stop_loss_price": None,
            "raw_snapshot": {"closes": closes[-20:], "volumes": volumes[-5:]},
        }


class BreakoutFailureStrategy(StrategyBase):
    name = "breakout_failure"
    type = "sell"

    def validate_preconditions(self, context: dict) -> bool:
        return context.get("data_quality_ok", True)

    def generate_signal(self, context: dict) -> dict | None:
        bars = context["kline_daily"]
        closes = [row.close for row in bars]
        highs = [row.high for row in bars]
        volumes = [row.volume for row in bars]
        if len(closes) < 10:
            return None
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
            "trigger_reason": "突破压力位后快速回落，收盘未站稳，存在突破失败风险，仅作为交易辅助",
            "risk_desc": "若继续跌破突破平台，应优先执行风控，仅作为交易辅助",
            "invalid_condition": "重新放量站上压力位并持续，仅作为交易辅助",
            "stop_loss_price": None,
            "raw_snapshot": {"pressure": pressure, "close": closes[-1], "high": highs[-1], "volume": volumes[-1]},
        }
