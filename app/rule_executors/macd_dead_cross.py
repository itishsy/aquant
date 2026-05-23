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


class MacdDeadCrossExecutor(RuleExecutor):
    executor_key = "macd_dead_cross"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "macd_dead_cross")
        rule_name = str(context.rule_config.get("rule_name") or "MACD Dead Cross")
        rule_type = str(context.rule_config.get("rule_type") or "sell_signal")
        timeframe = str(context.rule_config.get("timeframe") or "30m")
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
        macd = IndicatorService.calculate_macd(closes)
        dif = macd["dif"]
        dea = macd["dea"]
        hist = macd["hist"]
        crossed = dif[-2] >= dea[-2] and dif[-1] < dea[-1]
        weakening = dif[-1] < dif[-2] < dif[-3] and hist[-1] < hist[-2]
        triggered = crossed or weakening
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="A" if crossed else "B",
            trigger_price=closes[-1],
            trigger_time=_time(bars[-1]),
            reason=(
                f"{timeframe} MACD dead cross or weakening momentum detected."
                if triggered
                else f"{timeframe} MACD dead cross conditions are not met."
            ),
            risk_desc="Momentum is weakening; manual sell confirmation is required." if triggered else "",
            snapshot={
                "timeframe": timeframe,
                "crossed": crossed,
                "weakening": weakening,
                "closes": closes[-8:],
                "macd": macd,
                "executor_key": self.executor_key,
            },
        )


register_executor(MacdDeadCrossExecutor())
