from __future__ import annotations

from datetime import datetime
from typing import Any

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class VolumeSpikeExecutor(RuleExecutor):
    executor_key = "volume_spike"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "volume_spike")
        rule_name = str(context.rule_config.get("rule_name") or "Volume Spike")
        rule_type = str(context.rule_config.get("rule_type") or "confirm")
        signal = self._signal_config(context.rule_config)
        lookback = self._positive_int(signal.get("lookback_bars"), 20)
        multiplier = self._positive_float(signal.get("multiplier"), 1.5)
        bars = context.rule_config.get("kline_bars") or ((context.technical or {}).get("bars") or [])
        if len(bars) < lookback + 1:
            return self._not_ready(rule_code, rule_name, rule_type, f"Need {lookback + 1} bars for volume spike.", lookback, multiplier)

        latest = bars[-1]
        history = bars[-lookback - 1 : -1]
        latest_volume = self._bar_number(latest, "volume")
        history_volumes = [self._bar_number(bar, "volume") for bar in history]
        if latest_volume is None or any(value is None for value in history_volumes):
            return self._not_ready(rule_code, rule_name, rule_type, "Volume data is insufficient.", lookback, multiplier)
        average_volume = sum(history_volumes) / len(history_volumes)
        threshold = average_volume * multiplier
        triggered = latest_volume >= threshold
        latest_close = self._bar_number(latest, "close_price")
        latest_time = self._bar_time(latest)
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="B" if triggered else None,
            trigger_price=latest_close,
            trigger_time=latest_time or datetime.utcnow(),
            reason=(
                f"Latest volume {latest_volume} is above {multiplier}x average volume {average_volume}."
                if triggered
                else f"Latest volume {latest_volume} is below {multiplier}x average volume {average_volume}."
            ),
            snapshot={
                "latest_volume": latest_volume,
                "average_volume": average_volume,
                "threshold": threshold,
                "lookback_bars": lookback,
                "multiplier": multiplier,
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
    def _bar_number(bar: object, field: str) -> float | None:
        value = bar.get(field) if isinstance(bar, dict) else getattr(bar, field, None)
        if value in (None, ""):
            return None
        return float(value)

    @staticmethod
    def _bar_time(bar: object):
        return bar.get("kline_time") if isinstance(bar, dict) else getattr(bar, "kline_time", None)

    @staticmethod
    def _positive_int(value: Any, default: int) -> int:
        try:
            parsed = int(value or default)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    @staticmethod
    def _positive_float(value: Any, default: float) -> float:
        try:
            parsed = float(value if value is not None else default)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    @staticmethod
    def _not_ready(rule_code: str, rule_name: str, rule_type: str, reason: str, lookback: int, multiplier: float) -> RuleResult:
        return RuleResult(
            triggered=False,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            reason=reason,
            snapshot={"lookback_bars": lookback, "multiplier": multiplier, "executor_key": VolumeSpikeExecutor.executor_key},
        )


register_executor(VolumeSpikeExecutor())
