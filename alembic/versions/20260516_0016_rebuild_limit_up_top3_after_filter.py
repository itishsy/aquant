"""Rebuild limit-up top three after filtering ignored plates.

Revision ID: 20260516_0016
Revises: 20260516_0015
Create Date: 2026-05-16
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0016"
down_revision: str | None = "20260516_0015"
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


def _insert_row(conn, table_name: str, table_columns: set[str], values: dict[str, Any]) -> int | None:
    payload = {key: value for key, value in values.items() if key in table_columns}
    if not payload:
        return None
    columns_sql = ", ".join(payload.keys())
    values_sql = ", ".join(f":{key}" for key in payload)
    result = conn.execute(sa.text(f"INSERT INTO {table_name} ({columns_sql}) VALUES ({values_sql})"), payload)
    inserted_id = getattr(result, "lastrowid", None)
    return int(inserted_id) if inserted_id is not None else None


def upgrade() -> None:
    if not (_has_table("mkt_daily_plate") and _has_table("mkt_daily_plate_stock") and _has_table("mkt_limit_up_stock")):
        return

    conn = op.get_bind()
    plate_columns = _columns("mkt_daily_plate")
    plate_stock_columns = _columns("mkt_daily_plate_stock")
    limit_stock_columns = _columns("mkt_limit_up_stock")
    relation_column = _stock_relation_column(plate_stock_columns)
    required_plate = {"id", "trade_date", "plate_type", "platform", "rank_no", "plate_code", "plate_name"}
    required_stock = {"trade_date", "platform", "plate_code", "plate_name", "stock_code"}
    if not required_plate.issubset(plate_columns) or not required_stock.issubset(limit_stock_columns) or relation_column is None:
        return

    ignored_names = ["ST\u80a1", "\u5176\u4ed6", "\u5176\u5b83"]
    groups = conn.execute(
        sa.text(
            """
            SELECT trade_date, platform
            FROM mkt_limit_up_stock
            GROUP BY trade_date, platform
            """
        )
    ).mappings().all()

    for group in groups:
        existing_ids = [
            int(row["id"])
            for row in conn.execute(
                sa.text(
                    """
                    SELECT id
                    FROM mkt_daily_plate
                    WHERE plate_type='limit_up'
                      AND trade_date=:trade_date
                      AND platform=:platform
                    """
                ),
                {"trade_date": group["trade_date"], "platform": group["platform"]},
            ).mappings().all()
        ]
        if existing_ids:
            conn.execute(
                sa.text(f"DELETE FROM mkt_daily_plate_stock WHERE {relation_column} IN :ids").bindparams(
                    sa.bindparam("ids", expanding=True)
                ),
                {"ids": existing_ids},
            )
            conn.execute(
                sa.text("DELETE FROM mkt_daily_plate WHERE id IN :ids").bindparams(sa.bindparam("ids", expanding=True)),
                {"ids": existing_ids},
            )

        top_plates = conn.execute(
            sa.text(
                """
                SELECT
                    plate_code,
                    plate_name,
                    COUNT(*) AS stock_count,
                    GROUP_CONCAT(DISTINCT NULLIF(limit_reason, '') SEPARATOR '；') AS limit_reasons,
                    GROUP_CONCAT(DISTINCT NULLIF(reason_tags, '') SEPARATOR '；') AS reason_tags
                FROM mkt_limit_up_stock
                WHERE trade_date=:trade_date
                  AND platform=:platform
                  AND TRIM(plate_name) NOT IN :ignored_names
                GROUP BY plate_code, plate_name
                ORDER BY stock_count DESC, plate_code ASC
                LIMIT 3
                """
            ).bindparams(sa.bindparam("ignored_names", expanding=True)),
            {
                "trade_date": group["trade_date"],
                "platform": group["platform"],
                "ignored_names": ignored_names,
            },
        ).mappings().all()

        for rank_no, plate in enumerate(top_plates, start=1):
            now = datetime.utcnow()
            plate_id = _insert_row(
                conn,
                "mkt_daily_plate",
                plate_columns,
                {
                    "trade_date": group["trade_date"],
                    "plate_type": "limit_up",
                    "platform": group["platform"],
                    "rank_no": rank_no,
                    "plate_code": plate["plate_code"] or f"limit_up:{rank_no}",
                    "plate_name": plate["plate_name"] or "",
                    "description": plate.get("limit_reasons") or plate.get("reason_tags") or "",
                    "created_at": now,
                    "updated_at": now,
                },
            )
            if plate_id is None:
                continue

            stocks = conn.execute(
                sa.text(
                    """
                    SELECT stock_code, stock_name, change_pct, last_price
                    FROM mkt_limit_up_stock
                    WHERE trade_date=:trade_date
                      AND platform=:platform
                      AND plate_code=:plate_code
                      AND plate_name=:plate_name
                    ORDER BY id ASC
                    """
                ),
                {
                    "trade_date": group["trade_date"],
                    "platform": group["platform"],
                    "plate_code": plate["plate_code"],
                    "plate_name": plate["plate_name"],
                },
            ).mappings().all()
            for stock in stocks:
                now = datetime.utcnow()
                _insert_row(
                    conn,
                    "mkt_daily_plate_stock",
                    plate_stock_columns,
                    {
                        relation_column: plate_id,
                        "stock_code": stock["stock_code"] or "",
                        "stock_name": stock["stock_name"] or "",
                        "change_pct": stock.get("change_pct"),
                        "last_price": stock.get("last_price"),
                        "created_at": now,
                        "updated_at": now,
                    },
                )


def downgrade() -> None:
    # Data rebuild migration only.
    pass
