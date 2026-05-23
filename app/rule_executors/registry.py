from __future__ import annotations

from app.rule_executors.base import RuleExecutor


_EXECUTORS: dict[str, RuleExecutor] = {}


def register_executor(executor: RuleExecutor) -> RuleExecutor:
    executor_key = getattr(executor, "executor_key", "")
    if not executor_key:
        raise ValueError("executor_key is required")
    _EXECUTORS[executor_key] = executor
    return executor


def get_executor(executor_key: str) -> RuleExecutor | None:
    return _EXECUTORS.get(executor_key)


def list_executors() -> list[str]:
    return sorted(_EXECUTORS)
