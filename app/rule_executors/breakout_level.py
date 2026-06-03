from __future__ import annotations

from datetime import datetime
from typing import Any

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class BreakoutLevelExecutor(RuleExecutor):
    executor_key = "breakout_level"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "breakout_level")
        rule_name = str(context.rule_config.get("rule_name") or "Breakout Level")
        rule_type = str(context.rule_config.get("rule_type") or "buy_signal")
        signal = self._signal_config(context.rule_config)
        target_param = str(signal.get("target_param") or "").strip()
        target_raw = context.system_params.get(target_param) if target_param else None
        target_source = f"system_params.{target_param}" if target_raw not in (None, "") else "target_value"
        if target_raw in (None, ""):
            target_raw = signal.get("target_value")
        if target_raw in (None, ""):
            return self._not_ready(rule_code, rule_name, rule_type, "Missing breakout target.", {"target_param": target_param})
        try:
            target = float(target_raw)
            threshold_pct = float(signal.get("threshold_pct") or 0)
        except (TypeError, ValueError):
            return self._not_ready(rule_code, rule_name, rule_type, "Invalid breakout target or threshold_pct.", {"target_value": target_raw})

        breakout_type = str(signal.get("breakout_type") or signal.get("break_type") or "close_above").strip().lower()
        price_info = self._price_info(context, breakout_type)
        if price_info["price"] is None:
            return self._not_ready(rule_code, rule_name, rule_type, f"Missing price for breakout_type {breakout_type}.", {"target": target})

        price = float(price_info["price"])
        trigger_level = target * (1 + threshold_pct)
        triggered = price > trigger_level
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="B" if triggered else None,
            trigger_price=price,
            trigger_time=price_info["time"] or datetime.utcnow(),
            reason=(
                f"{price_info['label']} {price} broke above target {target} with threshold_pct {threshold_pct}."
                if triggered
                else f"{price_info['label']} {price} has not broken above target {target} with threshold_pct {threshold_pct}."
            ),
            snapshot={
                "target": target,
                "target_param": target_param,
                "target_source": target_source,
                "breakout_type": breakout_type,
                "threshold_pct": threshold_pct,
                "trigger_level": trigger_level,
                "price": price,
                "price_source": price_info["source"],
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
    def _price_info(context: RuleContext, breakout_type: str) -> dict[str, Any]:
        bars = context.rule_config.get("kline_bars") or ((context.technical or {}).get("bars") or [])
        latest_bar = bars[-1] if bars else None
        latest_time = getattr(latest_bar, "kline_time", None) if latest_bar is not None else context.rule_config.get("latest_time")
        if breakout_type == "intraday_above":
            if context.latest_price not in (None, ""):
                return {"price": context.latest_price, "source": "latest_price", "label": "Latest price", "time": latest_time}
            high_price = getattr(latest_bar, "high_price", None) if latest_bar is not None else None
            if high_price not in (None, ""):
                return {"price": high_price, "source": "latest_kline_high", "label": "Latest K-line high", "time": latest_time}
        close_price = context.rule_config.get("latest_close")
        if close_price in (None, "") and latest_bar is not None:
            close_price = getattr(latest_bar, "close_price", None)
        return {"price": close_price, "source": "latest_kline_close", "label": "Latest K-line close", "time": latest_time}

    @staticmethod
    def _not_ready(rule_code: str, rule_name: str, rule_type: str, reason: str, snapshot: dict[str, Any]) -> RuleResult:
        snapshot["executor_key"] = BreakoutLevelExecutor.executor_key
        return RuleResult(triggered=False, rule_code=rule_code, rule_name=rule_name, rule_type=rule_type, reason=reason, snapshot=snapshot)


register_executor(BreakoutLevelExecutor())
