"""Trading rule executor framework."""

from app.rule_executors.always_false import AlwaysFalseExecutor
from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.break_level import BreakLevelExecutor
from app.rule_executors.break_ma import BreakMaExecutor
from app.rule_executors.break_price import BreakPriceExecutor
from app.rule_executors.macd_bottom_divergence import MacdBottomDivergenceExecutor
from app.rule_executors.macd_dead_cross import MacdDeadCrossExecutor
from app.rule_executors.macd_top_divergence import MacdTopDivergenceExecutor
from app.rule_executors.not_break_price import NotBreakPriceExecutor
from app.rule_executors.pullback_to_level import PullbackToLevelExecutor
from app.rule_executors.registry import get_executor, list_executors, register_executor

__all__ = [
    "AlwaysFalseExecutor",
    "BreakLevelExecutor",
    "BreakMaExecutor",
    "BreakPriceExecutor",
    "MacdBottomDivergenceExecutor",
    "MacdDeadCrossExecutor",
    "MacdTopDivergenceExecutor",
    "NotBreakPriceExecutor",
    "PullbackToLevelExecutor",
    "RuleContext",
    "RuleExecutor",
    "RuleResult",
    "get_executor",
    "list_executors",
    "register_executor",
]
