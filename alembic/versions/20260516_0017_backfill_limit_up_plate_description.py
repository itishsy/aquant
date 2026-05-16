"""Backfill limit-up plate descriptions from stock reasons.

Revision ID: 20260516_0017
Revises: 20260516_0016
Create Date: 2026-05-16
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0017"
down_revision: str | None = "20260516_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if not (_has_table("mkt_daily_plate") and _has_table("mkt_limit_up_stock")):
        return

    plate_columns = _columns("mkt_daily_plate")
    stock_columns = _columns("mkt_limit_up_stock")
    required_plate = {"id", "trade_date", "plate_type", "platform", "plate_code", "plate_name", "description"}
    required_stock = {"trade_date", "platform", "plate_code", "plate_name"}
    if not required_plate.issubset(plate_columns) or not required_stock.issubset(stock_columns):
        return

    conn = op.get_bind()
    reason_parts = []
    if "limit_reason" in stock_columns:
        reason_parts.append("GROUP_CONCAT(DISTINCT NULLIF(s.limit_reason, '') SEPARATOR '；')")
    if "reason_tags" in stock_columns:
        reason_parts.append("GROUP_CONCAT(DISTINCT NULLIF(s.reason_tags, '') SEPARATOR '；')")
    if not reason_parts:
        return

    reason_expr = "COALESCE(" + ", ".join(reason_parts) + ", '')"
    rows = conn.execute(
        sa.text(
            f"""
            SELECT p.id, {reason_expr} AS description
            FROM mkt_daily_plate p
            JOIN mkt_limit_up_stock s
              ON s.trade_date=p.trade_date
             AND s.platform=p.platform
             AND s.plate_code=p.plate_code
             AND s.plate_name=p.plate_name
            WHERE p.plate_type='limit_up'
            GROUP BY p.id
            """
        )
    ).mappings().all()

    for row in rows:
        description = row.get("description") or ""
        if description:
            conn.execute(
                sa.text("UPDATE mkt_daily_plate SET description=:description WHERE id=:id"),
                {"description": description, "id": row["id"]},
            )


def downgrade() -> None:
    # Data backfill migration only.
    pass
