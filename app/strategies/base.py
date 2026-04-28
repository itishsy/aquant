from __future__ import annotations

from abc import ABC, abstractmethod


class StrategyBase(ABC):
    name: str
    type: str

    @abstractmethod
    def validate_preconditions(self, context: dict) -> bool: ...

    @abstractmethod
    def generate_signal(self, context: dict) -> dict | None: ...

    def scan(self, context: dict) -> dict | None:
        if not self.validate_preconditions(context):
            return None
        return self.generate_signal(context)
