from __future__ import annotations

from datetime import datetime
from typing import Any

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class BreakMaExecutor(RuleExecutor):
    executor_key = "break_ma"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "break_ma")
        rule_name = str(context.rule_config.get("rule_name") or "Break MA")
        rule_type = str(context.rule_config.get("rule_type") or "risk")
        signal_config = self._signal_config(context.rule_config)
        ma_window = self._ma_window(signal_config.get("ma"))
        break_type = str(signal_config.get("break_type") or "cross_down").strip().lower()
        bars = ((context.technical or {}).get("bars") or [])
        ma_values = (((context.technical or {}).get("indicators") or {}).get("ma") or {}).get(f"ma{ma_window}") or []

        if len(bars) < 2 or len(ma_values) < 2:
            return self._not_ready(rule_code, rule_name, rule_type, ma_window, break_type, "Need at least 2 bars and MA values.")

        previous_bar = bars[-2]
        latest_bar = bars[-1]
        previous_close = self._float_or_none(getattr(previous_bar, "close_price", None))
        latest_close = self._float_or_none(getattr(latest_bar, "close_price", None))
        previous_ma = self._float_or_none(ma_values[-2])
        latest_ma = self._float_or_none(ma_values[-1])
        if previous_close is None or latest_close is None or latest_ma is None:
            return self._not_ready(rule_code, rule_name, rule_type, ma_window, break_type, "Latest close or MA data is insufficient.")
        if break_type == "cross_down" and previous_ma is None:
            return self._not_ready(rule_code, rule_name, rule_type, ma_window, break_type, "Previous MA data is insufficient for cross_down.")

        if break_type == "below":
            triggered = latest_close < latest_ma
        else:
            break_type = "cross_down"
            triggered = previous_close >= previous_ma and latest_close < latest_ma

        latest_time = getattr(latest_bar, "kline_time", None)
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="S" if triggered else "B",
            trigger_price=latest_close,
            trigger_time=latest_time or datetime.utcnow(),
            reason=(
                f"Latest close {latest_close} broke MA{ma_window} {latest_ma} by {break_type}."
                if triggered
                else f"Latest close {latest_close} has not broken MA{ma_window} {latest_ma} by {break_type}."
            ),
            risk_desc=f"Price broke below MA{ma_window}; manual confirmation is required." if triggered else "",
            snapshot={
                "ma": ma_window,
                "break_type": break_type,
                "previous_close": previous_close,
                "latest_close": latest_close,
                "previous_ma": previous_ma,
                "latest_ma": latest_ma,
                "executor_key": self.executor_key,
            },
        )

    @staticmethod
    def _signal_config(rule_config: dict[str, Any]) -> dict[str, Any]:
        config_json = rule_config.get("config_json") if isinstance(rule_config, dict) else {}
        if isinstance(config_json, dict) and isinstance(config_json.get("signal"), dict):
            return config_json["signal"]
        return {}

    @staticmethod
    def _ma_window(value: Any) -> int:
        try:
            window = int(value or 5)
        except (TypeError, ValueError):
            return 5
        return window if window in {5, 10, 20} else 5

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _not_ready(rule_code: str, rule_name: str, rule_type: str, ma_window: int, break_type: str, reason: str) -> RuleResult:
        return RuleResult(
            triggered=False,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            reason=f"MA{ma_window} data not ready for {break_type}: {reason}",
            snapshot={"ma": ma_window, "break_type": break_type, "executor_key": BreakMaExecutor.executor_key},
        )


register_executor(BreakMaExecutor())
