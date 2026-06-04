from __future__ import annotations

from datetime import datetime
from typing import Any

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class MaTrendExecutor(RuleExecutor):
    executor_key = "ma_trend"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "ma_trend")
        rule_name = str(context.rule_config.get("rule_name") or "MA Trend")
        rule_type = str(context.rule_config.get("rule_type") or "filter")
        signal = self._signal_config(context.rule_config)
        mode = str(signal.get("mode") or "bullish_stack").strip().lower()
        ma_data = (((context.technical or {}).get("indicators") or {}).get("ma") or {})
        bars = (context.technical or {}).get("bars") or []
        latest_bar = bars[-1] if bars else None
        latest_close = self._bar_number(latest_bar, "close_price") if latest_bar is not None else None

        if mode == "price_not_below_ma":
            return self._evaluate_price_not_below_ma(
                rule_code, rule_name, rule_type, signal, ma_data, latest_bar, latest_close
            )

        ma5 = self._last(ma_data.get("ma5"))
        ma10 = self._last(ma_data.get("ma10"))
        ma20_values = ma_data.get("ma20") or []
        ma20 = self._last(ma20_values)
        if ma5 is None or ma10 is None or ma20 is None:
            return self._not_ready(rule_code, rule_name, rule_type, mode, "MA5/MA10/MA20 data is insufficient.")

        if mode == "price_above_ma20":
            if latest_close is None:
                return self._not_ready(rule_code, rule_name, rule_type, mode, "Latest close is missing.")
            triggered = latest_close > ma20
            reason = f"Latest close {latest_close} is {'above' if triggered else 'not above'} MA20 {ma20}."
        elif mode == "ma20_slope_up":
            slope_bars = self._positive_int(signal.get("slope_bars"), 3)
            if len(ma20_values) < slope_bars + 1 or self._last(ma20_values[-slope_bars - 1 : -slope_bars]) is None:
                return self._not_ready(rule_code, rule_name, rule_type, mode, "MA20 slope data is insufficient.")
            previous_ma20 = float(ma20_values[-slope_bars - 1])
            triggered = ma20 > previous_ma20
            reason = f"MA20 {ma20} is {'above' if triggered else 'not above'} MA20 {slope_bars} bars ago {previous_ma20}."
        elif mode == "bearish_stack":
            triggered = ma5 < ma10 < ma20
            reason = f"MA bearish stack is {'formed' if triggered else 'not formed'}: MA5 {ma5}, MA10 {ma10}, MA20 {ma20}."
        else:
            mode = "bullish_stack"
            triggered = ma5 > ma10 > ma20
            reason = f"MA bullish stack is {'formed' if triggered else 'not formed'}: MA5 {ma5}, MA10 {ma10}, MA20 {ma20}."

        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="B" if triggered else None,
            trigger_price=latest_close,
            trigger_time=self._bar_time(latest_bar) or datetime.utcnow(),
            reason=reason,
            snapshot={"mode": mode, "ma5": ma5, "ma10": ma10, "ma20": ma20, "latest_close": latest_close, "executor_key": self.executor_key},
        )

    def _evaluate_price_not_below_ma(
        self,
        rule_code: str,
        rule_name: str,
        rule_type: str,
        signal: dict[str, Any],
        ma_data: dict[str, Any],
        latest_bar: object | None,
        latest_close: float | None,
    ) -> RuleResult:
        mode = "price_not_below_ma"
        ma = self._ma_window(signal.get("ma"), 20)
        ma_key = f"ma{ma}"
        ma_values = ma_data.get(ma_key) or []
        latest_ma = self._last(ma_values)

        if latest_close is None:
            return self._not_ready(rule_code, rule_name, rule_type, mode, "Latest close is missing.")
        if latest_ma is None:
            return self._not_ready(rule_code, rule_name, rule_type, mode, f"MA{ma} data is insufficient.")

        triggered = latest_close >= latest_ma
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="B" if triggered else None,
            trigger_price=latest_close,
            trigger_time=self._bar_time(latest_bar) or datetime.utcnow(),
            reason=f"Latest close {latest_close} is {'not below' if triggered else 'below'} MA{ma} {latest_ma}.",
            snapshot={
                "mode": mode,
                "ma": ma,
                "latest_close": latest_close,
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
    def _ma_window(value: Any, default: int) -> int:
        try:
            window = int(value or default)
        except (TypeError, ValueError):
            return default
        return window if window in {5, 10, 20} else default

    @staticmethod
    def _last(values: Any) -> float | None:
        if not values:
            return None
        value = values[-1]
        if value in (None, ""):
            return None
        return float(value)

    @staticmethod
    def _bar_number(bar: object, field: str) -> float | None:
        value = bar.get(field) if isinstance(bar, dict) else getattr(bar, field, None)
        if value in (None, ""):
            return None
        return float(value)

    @staticmethod
    def _bar_time(bar: object | None):
        if bar is None:
            return None
        return bar.get("kline_time") if isinstance(bar, dict) else getattr(bar, "kline_time", None)

    @staticmethod
    def _positive_int(value: Any, default: int) -> int:
        try:
            parsed = int(value or default)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    @staticmethod
    def _not_ready(rule_code: str, rule_name: str, rule_type: str, mode: str, reason: str) -> RuleResult:
        return RuleResult(
            triggered=False,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            reason=reason,
            snapshot={"mode": mode, "executor_key": MaTrendExecutor.executor_key},
        )


register_executor(MaTrendExecutor())
