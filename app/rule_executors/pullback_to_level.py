from __future__ import annotations

from datetime import datetime
from typing import Any

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class PullbackToLevelExecutor(RuleExecutor):
    executor_key = "pullback_to_level"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "pullback_to_level")
        rule_name = str(context.rule_config.get("rule_name") or "Pullback To Level")
        rule_type = str(context.rule_config.get("rule_type") or "filter")
        signal_config = self._signal_config(context.rule_config)
        mode = str(signal_config.get("mode") or "from_recent_high").strip().lower()
        bars = (context.technical or {}).get("bars") or []
        latest_bar = bars[-1] if bars else None
        latest_close = self._float_or_none(getattr(latest_bar, "close_price", None))
        latest_time = getattr(latest_bar, "kline_time", None) if latest_bar is not None else None
        if latest_close is None:
            return self._not_ready(rule_code, rule_name, rule_type, mode, "Missing latest close.")

        if mode == "near_param_level":
            return self._near_param_level(context, rule_code, rule_name, rule_type, signal_config, latest_close, latest_time)
        return self._from_recent_high(rule_code, rule_name, rule_type, signal_config, bars, latest_close, latest_time)

    def _from_recent_high(
        self,
        rule_code: str,
        rule_name: str,
        rule_type: str,
        signal_config: dict[str, Any],
        bars: list[Any],
        latest_close: float,
        latest_time: datetime | None,
    ) -> RuleResult:
        highs = [self._float_or_none(getattr(bar, "high_price", None)) for bar in bars]
        highs = [value for value in highs if value is not None]
        if not highs:
            return self._not_ready(rule_code, rule_name, rule_type, "from_recent_high", "Missing recent high.")
        recent_high = max(highs)
        pullback_pct = self._float_or_none(signal_config.get("pullback_pct"))
        pullback_pct = 0.03 if pullback_pct is None else pullback_pct
        threshold = recent_high * (1 - pullback_pct)
        triggered = latest_close <= threshold
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="B" if triggered else None,
            trigger_price=latest_close,
            trigger_time=latest_time or datetime.utcnow(),
            reason=(
                f"Latest close {latest_close} pulled back from recent high {recent_high} by at least {pullback_pct}."
                if triggered
                else f"Latest close {latest_close} has not pulled back from recent high {recent_high} by {pullback_pct}."
            ),
            snapshot={
                "mode": "from_recent_high",
                "recent_high": recent_high,
                "target": None,
                "latest_close": latest_close,
                "threshold": threshold,
                "pullback_pct": pullback_pct,
                "executor_key": self.executor_key,
            },
        )

    def _near_param_level(
        self,
        context: RuleContext,
        rule_code: str,
        rule_name: str,
        rule_type: str,
        signal_config: dict[str, Any],
        latest_close: float,
        latest_time: datetime | None,
    ) -> RuleResult:
        target_param = str(signal_config.get("target_param") or "").strip()
        target = self._float_or_none(context.system_params.get(target_param)) if target_param else None
        if target is None:
            return RuleResult(
                triggered=False,
                rule_code=rule_code,
                rule_name=rule_name,
                rule_type=rule_type,
                reason="Missing target_param value for near_param_level.",
                snapshot={
                    "mode": "near_param_level",
                    "target_param": target_param,
                    "recent_high": None,
                    "target": None,
                    "latest_close": latest_close,
                    "threshold": None,
                    "executor_key": self.executor_key,
                },
            )
        near_pct = self._float_or_none(signal_config.get("near_pct"))
        near_pct = 0.01 if near_pct is None else near_pct
        lower = target * (1 - near_pct)
        upper = target * (1 + near_pct)
        triggered = lower <= latest_close <= upper
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="B" if triggered else None,
            trigger_price=latest_close,
            trigger_time=latest_time or datetime.utcnow(),
            reason=(
                f"Latest close {latest_close} is near {target_param} {target} within {near_pct}."
                if triggered
                else f"Latest close {latest_close} is not near {target_param} {target} within {near_pct}."
            ),
            snapshot={
                "mode": "near_param_level",
                "recent_high": None,
                "target": target,
                "target_param": target_param,
                "latest_close": latest_close,
                "threshold": {"lower": lower, "upper": upper},
                "near_pct": near_pct,
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
    def _float_or_none(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _not_ready(rule_code: str, rule_name: str, rule_type: str, mode: str, reason: str) -> RuleResult:
        return RuleResult(
            triggered=False,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            reason=f"Pullback data not ready for {mode}: {reason}",
            snapshot={"mode": mode, "recent_high": None, "target": None, "latest_close": None, "threshold": None},
        )


register_executor(PullbackToLevelExecutor())
