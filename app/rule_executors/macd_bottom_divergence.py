from __future__ import annotations

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor
from app.services.indicator import IndicatorService


def _value(row: object, attr: str) -> float:
    if isinstance(row, dict):
        return float(row[attr])
    return float(getattr(row, attr))


def _time(row: object):
    if isinstance(row, dict):
        return row.get("kline_time") or row.get("trade_time")
    return getattr(row, "kline_time", None) or getattr(row, "trade_time", None)


class MacdBottomDivergenceExecutor(RuleExecutor):
    executor_key = "macd_bottom_divergence"
    supported_timeframes = {"5m", "15m"}

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "macd_bottom_divergence")
        rule_name = str(context.rule_config.get("rule_name") or "MACD 底背离")
        rule_type = str(context.rule_config.get("rule_type") or "buy_signal")
        timeframe = str(context.rule_config.get("timeframe") or "15m")
        bars = context.rule_config.get("kline_bars") or []

        if timeframe not in self.supported_timeframes:
            return self._miss(rule_code, rule_name, rule_type, timeframe, "Unsupported timeframe.")
        if len(bars) < 8:
            return self._miss(rule_code, rule_name, rule_type, timeframe, "Not enough kline bars.")

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
        checks = {
            "price_lower": price_lower,
            "macd_higher": macd_higher,
            "dif_turning": dif_turning,
            "golden_cross_near": golden_cross_near,
            "volume_ok": volume_ok,
            "near_support": near_support,
        }
        if not all(checks.values()):
            return RuleResult(
                triggered=False,
                rule_code=rule_code,
                rule_name=rule_name,
                rule_type=rule_type,
                signal_level="B",
                trigger_price=closes[-1],
                trigger_time=_time(bars[-1]),
                reason=f"{timeframe} MACD bottom divergence conditions are not met.",
                snapshot={"timeframe": timeframe, "checks": checks, "closes": closes[-8:]},
            )

        return RuleResult(
            triggered=True,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="A",
            trigger_price=closes[-1],
            trigger_time=_time(bars[-1]),
            reason=f"{timeframe} price retests recent low while MACD momentum improves.",
            risk_desc="If price breaks the configured platform support, reassess the setup.",
            snapshot={
                "timeframe": timeframe,
                "checks": checks,
                "closes": closes,
                "volumes": volumes,
                "macd": macd,
                "executor_key": self.executor_key,
            },
        )

    @staticmethod
    def _miss(rule_code: str, rule_name: str, rule_type: str, timeframe: str, reason: str) -> RuleResult:
        return RuleResult(
            triggered=False,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            reason=reason,
            snapshot={"timeframe": timeframe, "reason": reason},
        )


register_executor(MacdBottomDivergenceExecutor())
