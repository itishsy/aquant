from __future__ import annotations

from datetime import datetime
from typing import Any

from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.registry import register_executor


class NearMaExecutor(RuleExecutor):
    executor_key = "near_ma"

    def execute(self, context: RuleContext) -> RuleResult:
        rule_code = str(context.rule_config.get("rule_code") or "near_ma")
        rule_name = str(context.rule_config.get("rule_name") or "Near MA")
        rule_type = str(context.rule_config.get("rule_type") or "filter")
        timeframe = str(context.rule_config.get("timeframe") or ((context.technical or {}).get("timeframe") or "daily"))
        signal_config = self._signal_config(context.rule_config)
        ma_window = self._ma_window(signal_config.get("ma"))
        near_pct = self._near_pct(signal_config.get("near_pct"))
        price_field = str(signal_config.get("price_field") or "close").strip().lower()

        technical = context.technical or {}
        bars = technical.get("bars") or []
        ma_values = ((technical.get("indicators") or {}).get("ma") or {}).get(f"ma{ma_window}") or []
        if not bars or not ma_values:
            return self._not_ready(rule_code, rule_name, rule_type, timeframe, ma_window, near_pct, "MA data is insufficient.")

        latest_bar = bars[-1]
        latest_close = self._bar_price(latest_bar, price_field)
        latest_ma = self._float_or_none(ma_values[-1])
        if latest_close is None or latest_ma is None:
            return self._not_ready(
                rule_code,
                rule_name,
                rule_type,
                timeframe,
                ma_window,
                near_pct,
                "Latest close or MA value is insufficient.",
            )

        lower = round(latest_ma * (1 - near_pct), 4)
        upper = round(latest_ma * (1 + near_pct), 4)
        triggered = lower <= latest_close <= upper
        latest_time = self._bar_time(latest_bar)
        return RuleResult(
            triggered=triggered,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            signal_level="B",
            trigger_price=latest_close,
            trigger_time=latest_time or datetime.utcnow(),
            reason=(
                f"Latest close {latest_close} has pulled back near MA{ma_window} {latest_ma}."
                if triggered
                else f"Latest close {latest_close} is not near MA{ma_window} {latest_ma}."
            ),
            snapshot={
                "latest_close": latest_close,
                "latest_ma": latest_ma,
                "lower": lower,
                "upper": upper,
                "ma": ma_window,
                "near_pct": near_pct,
                "timeframe": timeframe,
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
    def _ma_window(value: Any) -> int:
        try:
            window = int(value or 20)
        except (TypeError, ValueError):
            return 20
        return window if window > 0 else 20

    @staticmethod
    def _near_pct(value: Any) -> float:
        try:
            pct = float(value if value is not None else 0.02)
        except (TypeError, ValueError):
            return 0.02
        return pct if pct >= 0 else 0.02

    @classmethod
    def _bar_price(cls, bar: object, price_field: str) -> float | None:
        attr = f"{price_field}_price" if price_field in {"open", "high", "low", "close"} else price_field
        if isinstance(bar, dict):
            return cls._float_or_none(bar.get(attr) if attr in bar else bar.get(price_field))
        return cls._float_or_none(getattr(bar, attr, None) if hasattr(bar, attr) else getattr(bar, price_field, None))

    @staticmethod
    def _bar_time(bar: object):
        if isinstance(bar, dict):
            return bar.get("kline_time") or bar.get("trade_time")
        return getattr(bar, "kline_time", None) or getattr(bar, "trade_time", None)

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _not_ready(
        cls,
        rule_code: str,
        rule_name: str,
        rule_type: str,
        timeframe: str,
        ma_window: int,
        near_pct: float,
        reason: str,
    ) -> RuleResult:
        return RuleResult(
            triggered=False,
            rule_code=rule_code,
            rule_name=rule_name,
            rule_type=rule_type,
            reason=reason,
            snapshot={
                "ma": ma_window,
                "near_pct": near_pct,
                "timeframe": timeframe,
                "executor_key": cls.executor_key,
            },
        )


register_executor(NearMaExecutor())
