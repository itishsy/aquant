"""Rank limit-up plates and keep top three per day/platform.

Revision ID: 20260516_0014
Revises: 20260516_0013
Create Date: 2026-05-16
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0014"
down_revision: str | None = "20260516_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _stock_relation_column(stock_columns: set[str]) -> str | None:
    if "plate_id" in stock_columns:
        return "plate_id"
    if "daily_plate_id" in stock_columns:
        return "daily_plate_id"
    return None


def upgrade() -> None:
    if not (_has_table("mkt_daily_plate") and _has_table("mkt_daily_plate_stock")):
        return

    conn = op.get_bind()
    plate_columns = _columns("mkt_daily_plate")
    stock_columns = _columns("mkt_daily_plate_stock")
    if not {"id", "trade_date", "plate_type", "platform", "rank_no"}.issubset(plate_columns):
        return

    groups = conn.execute(
        sa.text(
            """
            SELECT trade_date, platform
            FROM mkt_daily_plate
            WHERE plate_type='limit_up'
            GROUP BY trade_date, platform
            """
        )
    ).mappings().all()

    relation_column = _stock_relation_column(stock_columns)
    for group in groups:
        stock_count_expr = "0"
        if relation_column:
            stock_count_expr = (
                f"(SELECT COUNT(*) FROM mkt_daily_plate_stock s WHERE s.{relation_column}=p.id)"
            )
        rows = conn.execute(
            sa.text(
                f"""
                SELECT p.id, {stock_count_expr} AS stock_count
                FROM mkt_daily_plate p
                WHERE p.plate_type='limit_up'
                  AND p.trade_date=:trade_date
                  AND p.platform=:platform
                ORDER BY stock_count DESC, p.id ASC
                """
            ),
            {"trade_date": group["trade_date"], "platform": group["platform"]},
        ).mappings().all()

        keep_ids: list[int] = []
        remove_ids: list[int] = []
        for index, row in enumerate(rows, start=1):
            row_id = int(row["id"])
            if index <= 3:
                keep_ids.append(row_id)
                conn.execute(sa.text("UPDATE mkt_daily_plate SET rank_no=:rank_no WHERE id=:id"), {"rank_no": index, "id": row_id})
            else:
                remove_ids.append(row_id)

        if remove_ids and relation_column:
            conn.execute(
                sa.text(f"DELETE FROM mkt_daily_plate_stock WHERE {relation_column} IN :ids").bindparams(
                    sa.bindparam("ids", expanding=True)
                ),
                {"ids": remove_ids},
            )
        if remove_ids:
            conn.execute(
                sa.text("DELETE FROM mkt_daily_plate WHERE id IN :ids").bindparams(sa.bindparam("ids", expanding=True)),
                {"ids": remove_ids},
            )


def downgrade() -> None:
    # Data cleanup/ranking migration only.
    pass
