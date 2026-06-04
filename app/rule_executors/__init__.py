"""Trading rule executor framework."""

from app.rule_executors.always_false import AlwaysFalseExecutor
from app.rule_executors.base import RuleContext, RuleExecutor, RuleResult
from app.rule_executors.breakout_level import BreakoutLevelExecutor
from app.rule_executors.break_level import BreakLevelExecutor
from app.rule_executors.break_ma import BreakMaExecutor
from app.rule_executors.ma_trend import MaTrendExecutor
from app.rule_executors.macd_bottom_divergence import MacdBottomDivergenceExecutor
from app.rule_executors.macd_dead_cross import MacdDeadCrossExecutor
from app.rule_executors.macd_top_divergence import MacdTopDivergenceExecutor
from app.rule_executors.profit_loss_threshold import ProfitLossThresholdExecutor
from app.rule_executors.pullback_to_level import PullbackToLevelExecutor
from app.rule_executors.volume_spike import VolumeSpikeExecutor
from app.rule_executors.registry import get_executor, list_executors, register_executor

__all__ = [
    "AlwaysFalseExecutor",
    "BreakoutLevelExecutor",
    "BreakLevelExecutor",
    "BreakMaExecutor",
    "MaTrendExecutor",
    "MacdBottomDivergenceExecutor",
    "MacdDeadCrossExecutor",
    "MacdTopDivergenceExecutor",
    "ProfitLossThresholdExecutor",
    "PullbackToLevelExecutor",
    "VolumeSpikeExecutor",
    "RuleContext",
    "RuleExecutor",
    "RuleResult",
    "get_executor",
    "list_executors",
    "register_executor",
]
