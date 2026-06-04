from __future__ import annotations

from alembic import op


revision = "20260604_remove_removed_rule_executors"
down_revision = "20260603_replace_break_price"
branch_labels = None
depends_on = None


REMOVED_RULE_CODES = (
    "not_break_platform_upper",
    "near_ma20_pullback",
    "near_key_level",
)

REMOVED_EXECUTOR_KEYS = (
    "not_break_price",
    "near_ma",
    "near_level",
)


def upgrade() -> None:
    rule_codes = ", ".join(f"'{code}'" for code in REMOVED_RULE_CODES)
    executor_keys = ", ".join(f"'{key}'" for key in REMOVED_EXECUTOR_KEYS)
    op.execute(f"DELETE FROM trading_system_rule_binding WHERE rule_code IN ({rule_codes})")
    op.execute(
        "DELETE FROM trading_rule_definition "
        f"WHERE rule_code IN ({rule_codes}) OR executor_key IN ({executor_keys})"
    )


def downgrade() -> None:
    # The executor implementations are intentionally removed in application code.
    # Recreating rows here would leave rule definitions pointing at missing executors.
    pass
