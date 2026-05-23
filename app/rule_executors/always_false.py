from __future__ import annotations

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class AlwaysFalseExecutor(RuleExecutor):
    executor_key = "always_false"

    def execute(self, context: RuleContext) -> RuleResult:
        return RuleResult(
            triggered=False,
            rule_code=str(context.rule_config.get("rule_code") or "always_false"),
            rule_name=str(context.rule_config.get("rule_name") or "Always False"),
            rule_type=str(context.rule_config.get("rule_type") or "filter"),
            trigger_price=context.latest_price,
            reason="Test executor always returns false.",
            snapshot={
                "watch_id": context.watch_id,
                "stock_code": context.stock_code,
                "stage": context.stage,
                "executor_key": self.executor_key,
            },
        )


register_executor(AlwaysFalseExecutor())
