from __future__ import annotations

from datetime import datetime
from typing import Any

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class BreakLevelExecutor(RuleExecutor):
    executor_key = "break_level"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "break_level")
        rule_name = str(context.rule_config.get("rule_name") or "Break Level")
        rule_type = str(context.rule_config.get("rule_type") or "risk")
        signal_config = self._signal_config(context.rule_config)
        target_param = str(signal_config.get("target_param") or "").strip()
        target_raw = context.system_params.get(target_param) if target_param else None
        target_source = f"system_params.{target_param}" if target_raw not in (None, "") else "target_value"
        if target_raw in (None, ""):
            target_raw = signal_config.get("target_value")
        if target_raw in (None, ""):
            return RuleResult(
                triggered=False,
                rule_code=rule_code,
                rule_name=rule_name,
                rule_type=rule_type,
                reason="Missing break target: provide signal.target_param in system_params or signal.target_value.",
                snapshot={"target_param": target_param, "target_value": signal_config.get("target_value")},
            )

        try:
            target = float(target_raw)
            threshold_pct = float(signal_config.get("threshold_pct") or 0)
        except (TypeError, ValueError):
            return RuleResult(
                triggered=False,
                rule_code=rule_code,
                rule_name=rule_name,
                rule_type=rule_type,
                reason="Invalid break target or threshold_pct.",
                snapshot={
                    "target_param": target_param,
                    "target_value": target_raw,
                    "threshold_pct": signal_config.get("threshold_pct"),
                },
            )

        break_type = str(signal_config.get("break_type") or "close_below").strip().lower()
        price_info = self._price_info(context, break_type)
        if price_info["price"] is None:
            return RuleResult(
                triggered=False,
                rule_code=rule_code,
                rule_name=rule_name,
                rule_type=rule_type,
                reason=f"Missing price for break_type {break_type}.",
                snapshot={
                    "target": target,
                    "target_source": target_source,
                    "break_type": break_type,
                    "price_source": price_info["source"],
                },
            )

        price = float(price_info["price"])
        trigger_level = target * (1 - threshold_pct)
        triggered = price < trigger_level
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="S" if triggered else "B",
            trigger_price=price,
            trigger_time=price_info["time"] or datetime.utcnow(),
            reason=(
                f"{price_info['label']} {price} broke below target {target} with threshold_pct {threshold_pct}."
                if triggered
                else f"{price_info['label']} {price} has not broken below target {target} with threshold_pct {threshold_pct}."
            ),
            risk_desc="Price broke the configured level; manual confirmation is required." if triggered else "",
            snapshot={
                "target": target,
                "target_param": target_param,
                "target_source": target_source,
                "target_value": signal_config.get("target_value"),
                "break_type": break_type,
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
    def _price_info(context: RuleContext, break_type: str) -> dict[str, Any]:
        bars = context.rule_config.get("kline_bars") or []
        latest_bar = bars[-1] if bars else None
        latest_time = getattr(latest_bar, "kline_time", None) if latest_bar is not None else context.rule_config.get("latest_time")
        if break_type == "intraday_below":
            if context.latest_price not in (None, ""):
                return {"price": context.latest_price, "source": "latest_price", "label": "Latest price", "time": latest_time}
            low_price = getattr(latest_bar, "low_price", None) if latest_bar is not None else None
            if low_price not in (None, ""):
                return {"price": low_price, "source": "latest_kline_low", "label": "Latest K-line low", "time": latest_time}
        close_price = context.rule_config.get("latest_close")
        if close_price in (None, "") and latest_bar is not None:
            close_price = getattr(latest_bar, "close_price", None)
        return {"price": close_price, "source": "latest_kline_close", "label": "Latest K-line close", "time": latest_time}


register_executor(BreakLevelExecutor())
