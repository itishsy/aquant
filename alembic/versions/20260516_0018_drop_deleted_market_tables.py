"""Drop deleted market tables no longer used by PRD v1 runtime.

Revision ID: 20260516_0018
Revises: 20260516_0017
Create Date: 2026-05-16
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0018"
down_revision: str | None = "20260516_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    for table_name in (
        "mkt_daily_chance_stock",
        "mkt_daily_chance",
        "mkt_daily_tuyere_stock",
        "mkt_daily_tuyere",
        "mkt_hot_board",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)


def downgrade() -> None:
    # Deleted legacy tables are intentionally not recreated.
    pass
