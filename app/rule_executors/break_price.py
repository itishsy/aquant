from __future__ import annotations

from datetime import datetime

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class BreakPriceExecutor(RuleExecutor):
    executor_key = "break_price"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "break_price")
        rule_name = str(context.rule_config.get("rule_name") or "Break Price")
        rule_type = str(context.rule_config.get("rule_type") or "stop_loss")
        support = context.system_params.get("platform_support_price")
        latest_close = context.rule_config.get("latest_close")
        latest_time = context.rule_config.get("latest_time") or datetime.utcnow()
        if support in (None, "") or latest_close in (None, ""):
            return RuleResult(
                triggered=False,
                rule_code=rule_code,
                rule_name=rule_name,
                rule_type=rule_type,
                reason="Missing platform_support_price or latest daily close.",
                snapshot={"platform_support_price": support, "latest_close": latest_close},
            )

        support_value = float(support)
        close_value = float(latest_close)
        triggered = close_value < support_value
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="S" if triggered else "B",
            trigger_price=close_value,
            trigger_time=latest_time,
            reason=(
                f"Daily close {close_value} broke platform support {support_value}."
                if triggered
                else f"Daily close {close_value} is above platform support {support_value}."
            ),
            risk_desc="Platform support is broken; manual stop-loss confirmation is required." if triggered else "",
            snapshot={
                "platform_support_price": support_value,
                "latest_close": close_value,
                "executor_key": self.executor_key,
            },
        )


register_executor(BreakPriceExecutor())
