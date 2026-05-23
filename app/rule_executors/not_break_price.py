from __future__ import annotations

from datetime import datetime

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class NotBreakPriceExecutor(RuleExecutor):
    executor_key = "not_break_price"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "not_break_price")
        rule_name = str(context.rule_config.get("rule_name") or "不跌破价格")
        rule_type = str(context.rule_config.get("rule_type") or "filter")
        target = context.system_params.get("platform_upper_price")
        latest_price = context.latest_price or context.rule_config.get("latest_close")
        if target in (None, "") or latest_price in (None, ""):
            return RuleResult(
                triggered=False,
                rule_code=rule_code,
                rule_name=rule_name,
                rule_type=rule_type,
                reason="Missing platform_upper_price or latest price.",
                snapshot={"target": target, "latest_price": latest_price},
            )

        target_value = float(target)
        price_value = float(latest_price)
        triggered = price_value >= target_value
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="B",
            trigger_price=price_value,
            trigger_time=context.rule_config.get("latest_time") or datetime.utcnow(),
            reason=(
                f"Latest price {price_value} is not below platform upper price {target_value}."
                if triggered
                else f"Latest price {price_value} is below platform upper price {target_value}."
            ),
            snapshot={
                "platform_upper_price": target_value,
                "latest_price": price_value,
                "executor_key": self.executor_key,
            },
        )


register_executor(NotBreakPriceExecutor())
