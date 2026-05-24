from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class RuleContext:
    watch_id: int
    stock_code: str
    stock_name: str
    trading_system_code: str | None
    stage: str
    system_params: dict[str, Any] = field(default_factory=dict)
    rule_config: dict[str, Any] = field(default_factory=dict)
    technical: dict[str, Any] | None = None
    trade_date: date | None = None
    latest_price: Decimal | float | None = None


@dataclass(frozen=True)
class RuleResult:
    triggered: bool
    rule_code: str
    rule_name: str
    rule_type: str
    signal_level: str | None = None
    trigger_price: Decimal | float | None = None
    trigger_time: datetime | None = None
    reason: str = ""
    risk_desc: str = ""
    snapshot: dict[str, Any] = field(default_factory=dict)


class RuleExecutor(ABC):
    executor_key: str

    @abstractmethod
    def execute(self, context: RuleContext) -> RuleResult:
        """Evaluate one rule against a prepared context."""
