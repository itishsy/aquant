from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models import TradingRuleDefinition, TradingSystemRuleBinding, WatchPool, WatchTrade


RequirementMap = dict[str, dict[str, dict[str, Any]]]


class RuleDataRequirementService:
    """Derive the minimum K-line data needed by enabled trading-system rules."""

    DEFAULT_EXECUTOR_REQUIREMENTS = {
        "macd_bottom_divergence": {"indicators": ["macd"], "lookback_bars": 120},
        "macd_top_divergence": {"indicators": ["macd"], "lookback_bars": 120},
        "macd_dead_cross": {"indicators": ["macd"], "lookback_bars": 120},
        "not_break_price": {"timeframe": "daily", "indicators": [], "lookback_bars": 5},
        "break_price": {"timeframe": "daily", "indicators": [], "lookback_bars": 5},
        "break_level": {"timeframe": "daily", "indicators": [], "lookback_bars": 5},
        "break_ma": {"indicators": ["ma"], "lookback_bars": 30},
        "pullback_to_level": {"indicators": [], "lookback_bars": 20},
    }

    def __init__(self, db: Session):
        self.db = db

    def build_watch_requirements(self, trade_date: date) -> RequirementMap:
        watches = (
            self.db.query(WatchPool)
            .filter(
                WatchPool.active.is_(True),
                WatchPool.status == "watching",
                WatchPool.system_stage == "observe",
                WatchPool.monitor_enabled.is_(True),
                WatchPool.signal_enabled.is_(True),
                WatchPool.trading_system_code.isnot(None),
                WatchPool.trading_system_code != "",
            )
            .order_by(WatchPool.id.asc())
            .all()
        )
        requirements: RequirementMap = {}
        for watch in watches:
            bindings = self._system_bindings(watch.trading_system_code, {"observe"})
            for binding, rule in bindings:
                self._merge_rule(requirements, watch.stock_code, binding, rule)
        return requirements

    def build_trade_requirements(self, trade_date: date) -> RequirementMap:
        trades = (
            self.db.query(WatchTrade)
            .filter(
                WatchTrade.trade_status.in_(["open", "holding"]),
                WatchTrade.current_stage == "trading",
                WatchTrade.trading_system_code.isnot(None),
                WatchTrade.trading_system_code != "",
            )
            .order_by(WatchTrade.id.asc())
            .all()
        )
        requirements: RequirementMap = {}
        for trade in trades:
            active_codes = set(trade.active_sell_rule_codes_json or []) | set(trade.active_stop_rule_codes_json or [])
            if not active_codes:
                continue
            bindings = self._system_bindings(trade.trading_system_code, {"trading", "sell", "stop_loss"}, active_codes)
            for binding, rule in bindings:
                self._merge_rule(requirements, trade.stock_code, binding, rule)
        return requirements

    def _system_bindings(
        self,
        system_code: str | None,
        stages: set[str],
        rule_codes: set[str] | None = None,
    ) -> list[tuple[TradingSystemRuleBinding, TradingRuleDefinition]]:
        if not system_code:
            return []
        query = (
            self.db.query(TradingSystemRuleBinding, TradingRuleDefinition)
            .join(TradingRuleDefinition, TradingRuleDefinition.rule_code == TradingSystemRuleBinding.rule_code)
            .filter(
                TradingSystemRuleBinding.system_code == system_code,
                TradingSystemRuleBinding.stage.in_(stages),
                TradingSystemRuleBinding.enabled.is_(True),
                TradingRuleDefinition.enabled.is_(True),
            )
        )
        if rule_codes:
            query = query.filter(TradingSystemRuleBinding.rule_code.in_(rule_codes))
        return query.order_by(TradingSystemRuleBinding.stage.asc(), TradingSystemRuleBinding.sort_order.asc()).all()

    def _merge_rule(
        self,
        requirements: RequirementMap,
        stock_code: str,
        binding: TradingSystemRuleBinding,
        rule: TradingRuleDefinition,
    ) -> None:
        requirement = self._rule_requirement(binding, rule)
        timeframe = requirement["timeframe"]
        stock_bucket = requirements.setdefault(stock_code, {})
        bucket = stock_bucket.setdefault(
            timeframe,
            {
                "timeframe": timeframe,
                "lookback_bars": 0,
                "indicators": [],
                "reasons": [],
            },
        )
        bucket["lookback_bars"] = max(bucket["lookback_bars"], requirement["lookback_bars"])
        bucket["indicators"] = self._merge_list(bucket["indicators"], requirement["indicators"])
        bucket["reasons"] = self._merge_list(bucket["reasons"], [rule.rule_code])

    def _rule_requirement(self, binding: TradingSystemRuleBinding, rule: TradingRuleDefinition) -> dict[str, Any]:
        return self.rule_requirement(binding, rule)

    def rule_requirement(self, binding: TradingSystemRuleBinding, rule: TradingRuleDefinition) -> dict[str, Any]:
        configured = (binding.config_json or {}).get("data") if isinstance(binding.config_json, dict) else None
        if isinstance(configured, dict):
            timeframe = configured.get("timeframe") or rule.timeframe
            lookback = configured.get("lookback_bars") or configured.get("lookback") or 0
            indicators = configured.get("indicators") or []
            return {
                "timeframe": self._normalize_timeframe(timeframe),
                "lookback_bars": int(lookback),
                "indicators": self._normalize_indicators(indicators),
            }

        default = self.DEFAULT_EXECUTOR_REQUIREMENTS.get(rule.executor_key, {"indicators": [], "lookback_bars": 0})
        return {
            "timeframe": self._normalize_timeframe(default.get("timeframe") or rule.timeframe),
            "lookback_bars": int(default.get("lookback_bars") or 0),
            "indicators": self._normalize_indicators(default.get("indicators") or []),
        }

    @staticmethod
    def _normalize_timeframe(timeframe: str) -> str:
        value = (timeframe or "").strip().lower()
        return "daily" if value == "1d" else value

    @staticmethod
    def _normalize_indicators(indicators: Any) -> list[str]:
        if isinstance(indicators, str):
            indicators = [indicators]
        if not isinstance(indicators, list):
            return []
        result = []
        for item in indicators:
            value = str(item or "").strip().lower()
            if value and value not in result:
                result.append(value)
        return result

    @staticmethod
    def _merge_list(left: list[str], right: list[str]) -> list[str]:
        result = list(left)
        for item in right:
            if item not in result:
                result.append(item)
        return result
