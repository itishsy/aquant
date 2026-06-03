from __future__ import annotations

from datetime import datetime
from typing import Any

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class NearLevelExecutor(RuleExecutor):
    executor_key = "near_level"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "near_level")
        rule_name = str(context.rule_config.get("rule_name") or "Near Level")
        rule_type = str(context.rule_config.get("rule_type") or "filter")
        signal = self._signal_config(context.rule_config)
        target_param = str(signal.get("target_param") or "").strip()
        target_raw = context.system_params.get(target_param) if target_param else None
        target_source = f"system_params.{target_param}" if target_raw not in (None, "") else "target_value"
        if target_raw in (None, ""):
            target_raw = signal.get("target_value")
        if target_raw in (None, ""):
            return self._not_ready(rule_code, rule_name, rule_type, "Missing near target.", {"target_param": target_param})
        try:
            target = float(target_raw)
            near_pct = float(signal.get("near_pct") if signal.get("near_pct") is not None else 0.02)
        except (TypeError, ValueError):
            return self._not_ready(rule_code, rule_name, rule_type, "Invalid near target or near_pct.", {"target_value": target_raw})

        price_field = str(signal.get("price_field") or "close").strip().lower()
        latest_bar = self._latest_bar(context)
        price = context.latest_price if price_field == "latest_price" else self._bar_price(latest_bar, price_field)
        if price in (None, ""):
            return self._not_ready(rule_code, rule_name, rule_type, f"Missing price for field {price_field}.", {"target": target})

        price_value = float(price)
        lower = target * (1 - near_pct)
        upper = target * (1 + near_pct)
        triggered = lower <= price_value <= upper
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="B" if triggered else None,
            trigger_price=price_value,
            trigger_time=self._bar_time(latest_bar) or datetime.utcnow(),
            reason=(
                f"{price_field} {price_value} is near target {target} within {near_pct}."
                if triggered
                else f"{price_field} {price_value} is not near target {target} within {near_pct}."
            ),
            snapshot={
                "target": target,
                "target_param": target_param,
                "target_source": target_source,
                "near_pct": near_pct,
                "lower": lower,
                "upper": upper,
                "price": price_value,
                "price_field": price_field,
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
    def _latest_bar(context: RuleContext):
        bars = context.rule_config.get("kline_bars") or ((context.technical or {}).get("bars") or [])
        return bars[-1] if bars else None

    @staticmethod
    def _bar_price(bar: object | None, price_field: str) -> float | None:
        if bar is None:
            return None
        attr = f"{price_field}_price" if price_field in {"open", "high", "low", "close"} else price_field
        value = bar.get(attr) if isinstance(bar, dict) else getattr(bar, attr, None)
        if value in (None, ""):
            return None
        return float(value)

    @staticmethod
    def _bar_time(bar: object | None):
        if bar is None:
            return None
        return bar.get("kline_time") if isinstance(bar, dict) else getattr(bar, "kline_time", None)

    @staticmethod
    def _not_ready(rule_code: str, rule_name: str, rule_type: str, reason: str, snapshot: dict[str, Any]) -> RuleResult:
        snapshot["executor_key"] = NearLevelExecutor.executor_key
        return RuleResult(triggered=False, rule_code=rule_code, rule_name=rule_name, rule_type=rule_type, reason=reason, snapshot=snapshot)


register_executor(NearLevelExecutor())
