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


class MacdTopDivergenceExecutor(RuleExecutor):
    executor_key = "macd_top_divergence"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "macd_top_divergence")
        rule_name = str(context.rule_config.get("rule_name") or "MACD Top Divergence")
        rule_type = str(context.rule_config.get("rule_type") or "sell_signal")
        timeframe = str(context.rule_config.get("timeframe") or "5m")
        bars = context.rule_config.get("kline_bars") or []
        if len(bars) < 8:
            return RuleResult(
                triggered=False,
                rule_code=rule_code,
                rule_name=rule_name,
                rule_type=rule_type,
                reason="Not enough kline bars.",
                snapshot={"timeframe": timeframe, "bar_count": len(bars)},
            )

        closes = [_value(row, "close_price") for row in bars]
        volumes = [_value(row, "volume") for row in bars]
        macd = IndicatorService.calculate_macd(closes)
        recent_window = closes[-8:]
        prior_high = max(recent_window[:4])
        recent_high = max(recent_window[4:])
        price_higher = recent_high >= prior_high * 0.99 and closes[-1] < recent_high
        recent_hist = macd["hist"][-6:]
        macd_lower = max(recent_hist[3:]) < max(recent_hist[:3])
        dif_turning = macd["dif"][-1] < macd["dif"][-2] < macd["dif"][-3]
        volume_warning = volumes[-1] >= max(volumes[-4:]) * 0.85
        checks = {
            "price_higher": price_higher,
            "macd_lower": macd_lower,
            "dif_turning": dif_turning,
            "volume_warning": volume_warning,
        }
        triggered = all(checks.values())
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="A" if triggered else "B",
            trigger_price=closes[-1],
            trigger_time=_time(bars[-1]),
            reason=(
                f"{timeframe} price retests high while MACD momentum weakens."
                if triggered
                else f"{timeframe} MACD top divergence conditions are not met."
            ),
            risk_desc="Potential sell point; manual confirmation is required." if triggered else "",
            snapshot={
                "timeframe": timeframe,
                "checks": checks,
                "closes": closes[-8:],
                "volumes": volumes[-8:],
                "macd": macd,
                "executor_key": self.executor_key,
            },
        )


register_executor(MacdTopDivergenceExecutor())
