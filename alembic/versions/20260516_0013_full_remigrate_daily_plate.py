"""Fully remigrate legacy plate rows without deduplication.

Revision ID: 20260516_0013
Revises: 20260516_0012
Create Date: 2026-05-16
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0013"
down_revision: str | None = "20260516_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _drop_blocking_unique_constraints(plate_columns: set[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    required = {"trade_date", "plate_type", "platform", "plate_code"}
    for constraint in inspector.get_unique_constraints("mkt_daily_plate"):
        name = constraint.get("name")
        columns = set(constraint.get("column_names") or [])
        if not name:
            continue
        if required.issubset(columns):
            continue
        if "trade_date" in columns and ("plate_type" in columns or "source" in columns):
            op.drop_constraint(name, "mkt_daily_plate", type_="unique")
    refreshed = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("mkt_daily_plate")}
    if required.issubset(refreshed):
        existing = {
            constraint.get("name")
            for constraint in sa.inspect(op.get_bind()).get_unique_constraints("mkt_daily_plate")
        }
        if "uq_mkt_daily_plate_identity" not in existing:
            op.create_unique_constraint(
                "uq_mkt_daily_plate_identity",
                "mkt_daily_plate",
                ["trade_date", "plate_type", "platform", "plate_code"],
            )


def _stock_relation_column(stock_columns: set[str]) -> str | None:
    if "plate_id" in stock_columns:
        return "plate_id"
    if "daily_plate_id" in stock_columns:
        return "daily_plate_id"
    return None


def _delete_existing(conn, plate_type: str, plate_columns: set[str], stock_columns: set[str]) -> None:
    relation_column = _stock_relation_column(stock_columns)
    if relation_column:
        ids = [
            row[0]
            for row in conn.execute(
                sa.text("SELECT id FROM mkt_daily_plate WHERE plate_type=:plate_type"),
                {"plate_type": plate_type},
            ).all()
        ]
        if ids:
            conn.execute(
                sa.text(f"DELETE FROM mkt_daily_plate_stock WHERE {relation_column} IN :ids").bindparams(
                    sa.bindparam("ids", expanding=True)
                ),
                {"ids": ids},
            )
    if "plate_type" in plate_columns:
        conn.execute(sa.text("DELETE FROM mkt_daily_plate WHERE plate_type=:plate_type"), {"plate_type": plate_type})


def _safe_plate_code(raw_code: object, row_id: object, kind: str, duplicate_keys: set[tuple], trade_date: object, platform: str) -> str:
    raw = "" if raw_code is None else str(raw_code)
    key = (kind, trade_date, platform, raw)
    if raw and key not in duplicate_keys:
        return raw
    return f"{kind}:{row_id}"


def _insert_plate(conn, plate_columns: set[str], values: dict) -> int | None:
    insert_columns = [
        name
        for name in (
            "trade_date",
            "plate_type",
            "platform",
            "rank_no",
            "plate_code",
            "plate_name",
            "article_title",
            "description",
            "jump_url",
            "change_pct",
            "raw_score",
            "limit_up_count",
            "up_reason",
            "source_update_time",
            "collected_at",
            "created_at",
            "updated_at",
        )
        if name in plate_columns
    ]
    if not {"trade_date", "plate_type"}.issubset(insert_columns):
        return None
    conn.execute(
        sa.text(
            f"INSERT INTO mkt_daily_plate ({', '.join(insert_columns)}) "
            f"VALUES ({', '.join(f':{name}' for name in insert_columns)})"
        ),
        values,
    )
    return int(conn.execute(sa.text("SELECT LAST_INSERT_ID()")).scalar() or 0) if conn.dialect.name in {"mysql", "mariadb"} else None


def _find_inserted_plate_id(conn, plate_columns: set[str], values: dict) -> int | None:
    where = ["trade_date=:trade_date", "plate_type=:plate_type"]
    params = {"trade_date": values["trade_date"], "plate_type": values["plate_type"]}
    if "platform" in plate_columns:
        where.append("platform=:platform")
        params["platform"] = values.get("platform") or "cls"
    if "plate_code" in plate_columns:
        where.append("plate_code=:plate_code")
        params["plate_code"] = values.get("plate_code") or ""
    row = conn.execute(
        sa.text(f"SELECT id FROM mkt_daily_plate WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 1"),
        params,
    ).first()
    return int(row[0]) if row else None


def _insert_plate_stock(conn, stock_columns: set[str], plate_id: int, stock: dict) -> None:
    relation_column = _stock_relation_column(stock_columns)
    if not relation_column or "stock_code" not in stock_columns or not stock.get("stock_code"):
        return
    values = {
        relation_column: plate_id,
        "stock_code": stock.get("stock_code") or "",
        "stock_name": stock.get("stock_name") or "",
        "change_pct": stock.get("change_pct"),
        "last_price": stock.get("last_price"),
    }
    insert_columns = [
        name
        for name in (relation_column, "stock_code", "stock_name", "change_pct", "last_price", "created_at", "updated_at")
        if name in stock_columns
    ]
    values.setdefault("created_at", None)
    values.setdefault("updated_at", None)
    conn.execute(
        sa.text(
            f"INSERT INTO mkt_daily_plate_stock ({', '.join(insert_columns)}) "
            f"VALUES ({', '.join('CURRENT_TIMESTAMP' if name in {'created_at', 'updated_at'} else f':{name}' for name in insert_columns)})"
        ),
        values,
    )


def _duplicate_keys(rows: list[dict], kind: str, id_key: str) -> set[tuple]:
    counter = Counter(
        (
            kind,
            row.get("trade_date"),
            row.get("platform") or "cls",
            "" if row.get(id_key) is None else str(row.get(id_key)),
        )
        for row in rows
    )
    return {key for key, count in counter.items() if count > 1 or not key[1]}


def _migrate_chance(conn, plate_columns: set[str], stock_columns: set[str]) -> None:
    if not _has_table("mkt_daily_chance"):
        return
    rows = [dict(row) for row in conn.execute(sa.text("SELECT * FROM mkt_daily_chance ORDER BY trade_date, rank_no, id")).mappings().all()]
    duplicate_keys = _duplicate_keys(rows, "chance", "subject_id")
    for src in rows:
        plate_name = src.get("subject_name") or src.get("article_title") or ""
        article_title = src.get("article_title") or plate_name
        values = {
            "trade_date": src["trade_date"],
            "plate_type": "chance",
            "platform": src.get("platform") or "cls",
            "rank_no": src.get("rank_no"),
            "plate_code": _safe_plate_code(src.get("subject_id"), src.get("id"), "chance", duplicate_keys, src["trade_date"], src.get("platform") or "cls"),
            "plate_name": plate_name,
            "article_title": article_title,
            "description": src.get("description") or article_title,
            "jump_url": src.get("jump_url"),
            "change_pct": None,
            "raw_score": None,
            "limit_up_count": None,
            "up_reason": article_title,
            "source_update_time": src.get("source_update_time"),
            "collected_at": src.get("collected_at"),
            "created_at": src.get("created_at"),
            "updated_at": src.get("updated_at"),
        }
        plate_id = _insert_plate(conn, plate_columns, values) or _find_inserted_plate_id(conn, plate_columns, values)
        if plate_id and _has_table("mkt_daily_chance_stock"):
            stocks = conn.execute(sa.text("SELECT * FROM mkt_daily_chance_stock WHERE chance_id=:id"), {"id": src["id"]}).mappings().all()
            for stock in stocks:
                _insert_plate_stock(conn, stock_columns, plate_id, dict(stock))


def _migrate_tuyere(conn, plate_columns: set[str], stock_columns: set[str]) -> None:
    if not _has_table("mkt_daily_tuyere"):
        return
    rows = [dict(row) for row in conn.execute(sa.text("SELECT * FROM mkt_daily_tuyere ORDER BY trade_date, rank_no, id")).mappings().all()]
    duplicate_keys = _duplicate_keys(rows, "tuyere", "subject_id")
    for src in rows:
        plate_name = src.get("subject_name") or src.get("driver") or ""
        values = {
            "trade_date": src["trade_date"],
            "plate_type": "tuyere",
            "platform": src.get("platform") or "cls",
            "rank_no": src.get("rank_no"),
            "plate_code": _safe_plate_code(src.get("subject_id"), src.get("id"), "tuyere", duplicate_keys, src["trade_date"], src.get("platform") or "cls"),
            "plate_name": plate_name,
            "article_title": plate_name,
            "description": src.get("description") or src.get("driver") or "",
            "jump_url": src.get("jump_url"),
            "change_pct": None,
            "raw_score": None,
            "limit_up_count": None,
            "up_reason": src.get("driver") or "",
            "source_update_time": src.get("source_update_time"),
            "collected_at": src.get("collected_at"),
            "created_at": src.get("created_at"),
            "updated_at": src.get("updated_at"),
        }
        plate_id = _insert_plate(conn, plate_columns, values) or _find_inserted_plate_id(conn, plate_columns, values)
        if plate_id and _has_table("mkt_daily_tuyere_stock"):
            stocks = conn.execute(sa.text("SELECT * FROM mkt_daily_tuyere_stock WHERE tuyere_id=:id"), {"id": src["id"]}).mappings().all()
            for stock in stocks:
                _insert_plate_stock(conn, stock_columns, plate_id, dict(stock))


def _migrate_limit_up(conn, plate_columns: set[str], stock_columns: set[str]) -> None:
    if not _has_table("mkt_limit_up_plate"):
        return
    rows = [dict(row) for row in conn.execute(sa.text("SELECT * FROM mkt_limit_up_plate ORDER BY trade_date, id")).mappings().all()]
    duplicate_keys = _duplicate_keys(rows, "limit_up", "plate_code")
    for src in rows:
        values = {
            "trade_date": src["trade_date"],
            "plate_type": "limit_up",
            "platform": src.get("platform") or "cls",
            "rank_no": src.get("rank_no"),
            "plate_code": _safe_plate_code(src.get("plate_code"), src.get("id"), "limit_up", duplicate_keys, src["trade_date"], src.get("platform") or "cls"),
            "plate_name": src.get("plate_name") or "",
            "article_title": src.get("plate_name") or "",
            "description": src.get("up_reason") or "",
            "jump_url": src.get("jump_url"),
            "change_pct": src.get("change_pct"),
            "raw_score": src.get("limit_up_count"),
            "limit_up_count": src.get("limit_up_count"),
            "up_reason": src.get("up_reason") or "",
            "source_update_time": src.get("source_update_time"),
            "collected_at": src.get("collected_at"),
            "created_at": src.get("created_at"),
            "updated_at": src.get("updated_at"),
        }
        plate_id = _insert_plate(conn, plate_columns, values) or _find_inserted_plate_id(conn, plate_columns, values)
        if plate_id and _has_table("mkt_limit_up_stock"):
            stocks = conn.execute(
                sa.text(
                    """
                    SELECT stock_code, stock_name, change_pct, last_price
                    FROM mkt_limit_up_stock
                    WHERE trade_date=:trade_date AND platform=:platform AND plate_code=:source_plate_code
                    """
                ),
                {**values, "source_plate_code": src.get("plate_code") or ""},
            ).mappings().all()
            for stock in stocks:
                _insert_plate_stock(conn, stock_columns, plate_id, dict(stock))


def upgrade() -> None:
    if not (_has_table("mkt_daily_plate") and _has_table("mkt_daily_plate_stock")):
        return
    conn = op.get_bind()
    plate_columns = _columns("mkt_daily_plate")
    stock_columns = _columns("mkt_daily_plate_stock")
    if "plate_type" not in plate_columns:
        return
    _drop_blocking_unique_constraints(plate_columns)
    for plate_type in ("chance", "tuyere", "limit_up"):
        _delete_existing(conn, plate_type, plate_columns, stock_columns)
    _migrate_chance(conn, plate_columns, stock_columns)
    _migrate_tuyere(conn, plate_columns, stock_columns)
    _migrate_limit_up(conn, plate_columns, stock_columns)


def downgrade() -> None:
    # Data-only migration. Keep copied records in place on downgrade.
    pass
