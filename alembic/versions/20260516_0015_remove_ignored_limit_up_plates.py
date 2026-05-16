"""Remove ignored limit-up plate categories.

Revision ID: 20260516_0015
Revises: 20260516_0014
Create Date: 2026-05-16
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0015"
down_revision: str | None = "20260516_0014"
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


def _delete_plate_rows(conn, ids: list[int], relation_column: str | None) -> None:
    if not ids:
        return
    if relation_column:
        conn.execute(
            sa.text(f"DELETE FROM mkt_daily_plate_stock WHERE {relation_column} IN :ids").bindparams(
                sa.bindparam("ids", expanding=True)
            ),
            {"ids": ids},
        )
    conn.execute(
        sa.text("DELETE FROM mkt_daily_plate WHERE id IN :ids").bindparams(sa.bindparam("ids", expanding=True)),
        {"ids": ids},
    )


def _rerank_limit_up_plates(conn, relation_column: str | None) -> None:
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

    for group in groups:
        stock_count_expr = "0"
        if relation_column:
            stock_count_expr = f"(SELECT COUNT(*) FROM mkt_daily_plate_stock s WHERE s.{relation_column}=p.id)"
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

        remove_ids: list[int] = []
        for index, row in enumerate(rows, start=1):
            row_id = int(row["id"])
            if index <= 3:
                conn.execute(sa.text("UPDATE mkt_daily_plate SET rank_no=:rank_no WHERE id=:id"), {"rank_no": index, "id": row_id})
            else:
                remove_ids.append(row_id)
        _delete_plate_rows(conn, remove_ids, relation_column)


def upgrade() -> None:
    if not _has_table("mkt_daily_plate"):
        return
    plate_columns = _columns("mkt_daily_plate")
    if not {"id", "plate_type", "plate_name"}.issubset(plate_columns):
        return

    conn = op.get_bind()
    relation_column = None
    if _has_table("mkt_daily_plate_stock"):
        relation_column = _stock_relation_column(_columns("mkt_daily_plate_stock"))

    ignored_ids = [
        int(row["id"])
        for row in conn.execute(
            sa.text(
                """
                SELECT id
                FROM mkt_daily_plate
                WHERE plate_type='limit_up'
                  AND TRIM(plate_name) IN :ignored_names
                """
            ).bindparams(sa.bindparam("ignored_names", expanding=True)),
            {"ignored_names": ["ST\u80a1", "\u5176\u4ed6", "\u5176\u5b83"]},
        ).mappings().all()
    ]
    _delete_plate_rows(conn, ignored_ids, relation_column)
    _rerank_limit_up_plates(conn, relation_column)


def downgrade() -> None:
    # Data cleanup migration only.
    pass
