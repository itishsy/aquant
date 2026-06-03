from __future__ import annotations

from datetime import datetime
from typing import Any

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class ProfitLossThresholdExecutor(RuleExecutor):
    executor_key = "profit_loss_threshold"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "profit_loss_threshold")
        rule_name = str(context.rule_config.get("rule_name") or "Profit/Loss Threshold")
        rule_type = str(context.rule_config.get("rule_type") or "sell_signal")
        signal = self._signal_config(context.rule_config)
        mode = str(signal.get("mode") or "profit_ratio_ge").strip().lower()
        threshold = self._float_or_none(signal.get("threshold"))
        if threshold is None:
            return self._not_ready(rule_code, rule_name, rule_type, mode, "Missing threshold.")

        latest_price = self._float_or_none(context.latest_price) or self._float_or_none(context.rule_config.get("latest_price"))
        average_buy_price = self._float_or_none(context.rule_config.get("average_buy_price") or context.rule_config.get("first_buy_price"))
        if latest_price is None or average_buy_price is None or average_buy_price == 0:
            return self._not_ready(rule_code, rule_name, rule_type, mode, "Missing latest_price or average_buy_price.")
        pnl_ratio = (latest_price - average_buy_price) / average_buy_price
        remaining_amount = self._float_or_none(context.rule_config.get("remaining_amount")) or 0
        pnl_amount = (latest_price - average_buy_price) * remaining_amount if remaining_amount else None

        if mode == "loss_ratio_le":
            triggered = pnl_ratio <= threshold
        elif mode == "profit_amount_ge":
            triggered = pnl_amount is not None and pnl_amount >= threshold
        elif mode == "loss_amount_le":
            triggered = pnl_amount is not None and pnl_amount <= threshold
        else:
            mode = "profit_ratio_ge"
            triggered = pnl_ratio >= threshold

        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="S" if mode.startswith("loss") and triggered else ("B" if triggered else None),
            trigger_price=latest_price,
            trigger_time=context.rule_config.get("latest_time") or datetime.utcnow(),
            reason=(
                f"PnL {mode} triggered: ratio {pnl_ratio:.4f}, amount {pnl_amount}, threshold {threshold}."
                if triggered
                else f"PnL {mode} not triggered: ratio {pnl_ratio:.4f}, amount {pnl_amount}, threshold {threshold}."
            ),
            risk_desc="Profit/loss threshold reached; manual trade decision is required." if triggered else "",
            snapshot={
                "mode": mode,
                "threshold": threshold,
                "latest_price": latest_price,
                "average_buy_price": average_buy_price,
                "remaining_amount": remaining_amount,
                "pnl_ratio": pnl_ratio,
                "pnl_amount": pnl_amount,
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
            reason=reason,
            snapshot={"mode": mode, "executor_key": ProfitLossThresholdExecutor.executor_key},
        )


register_executor(ProfitLossThresholdExecutor())
