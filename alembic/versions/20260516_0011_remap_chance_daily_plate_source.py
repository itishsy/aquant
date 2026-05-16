"""Migrate legacy plate data into mkt_daily_plate.

Revision ID: 20260516_0011
Revises: 20260516_0010
Create Date: 2026-05-16
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0011"
down_revision: str | None = "20260516_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _insert_ignore_prefix() -> str:
    dialect = op.get_bind().dialect.name
    if dialect in {"mysql", "mariadb"}:
        return "INSERT IGNORE"
    if dialect == "sqlite":
        return "INSERT OR IGNORE"
    return "INSERT"


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _first_existing(columns: set[str], *names: str) -> str | None:
    for name in names:
        if name in columns:
            return name
    return None


def _find_plate_id(conn, plate_columns: set[str], values: dict) -> int | None:
    where = ["trade_date=:trade_date", "plate_type=:plate_type"]
    params = {"trade_date": values["trade_date"], "plate_type": values["plate_type"]}
    if "platform" in plate_columns:
        where.append("platform=:platform")
        params["platform"] = values.get("platform") or "cls"
    if "plate_code" in plate_columns and values.get("plate_code"):
        where.append("plate_code=:plate_code")
        params["plate_code"] = values["plate_code"]
    elif "plate_name" in plate_columns and values.get("plate_name"):
        where.append("plate_name=:plate_name")
        params["plate_name"] = values["plate_name"]
    row = conn.execute(sa.text(f"SELECT id FROM mkt_daily_plate WHERE {' AND '.join(where)} LIMIT 1"), params).first()
    return int(row[0]) if row else None


def _upsert_plate(conn, plate_columns: set[str], values: dict) -> int | None:
    insert_columns = [
        name
        for name in (
            "trade_date",
            "plate_type",
            "platform",
            "rank_no",
            "plate_code",
            "plate_name",
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

    plate_id = _find_plate_id(conn, plate_columns, values)
    if plate_id:
        update_columns = [name for name in insert_columns if name not in {"trade_date", "plate_type", "created_at"}]
        if update_columns:
            assignments = ", ".join(f"{name}=:{name}" for name in update_columns)
            conn.execute(sa.text(f"UPDATE mkt_daily_plate SET {assignments} WHERE id=:id"), {**values, "id": plate_id})
        return plate_id

    prefix = _insert_ignore_prefix()
    columns_sql = ", ".join(insert_columns)
    values_sql = ", ".join(f":{name}" for name in insert_columns)
    conn.execute(sa.text(f"{prefix} INTO mkt_daily_plate ({columns_sql}) VALUES ({values_sql})"), values)
    return _find_plate_id(conn, plate_columns, values)


def _insert_plate_stock(conn, stock_columns: set[str], plate_id: int, stock: dict) -> None:
    relation_column = _first_existing(stock_columns, "plate_id", "daily_plate_id")
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
        for name in (relation_column, "stock_code", "stock_name", "change_pct", "last_price")
        if name in stock_columns
    ]
    prefix = _insert_ignore_prefix()
    columns_sql = ", ".join(insert_columns)
    values_sql = ", ".join(f":{name}" for name in insert_columns)
    conn.execute(sa.text(f"{prefix} INTO mkt_daily_plate_stock ({columns_sql}) VALUES ({values_sql})"), values)


def _migrate_chances(conn, plate_columns: set[str], stock_columns: set[str]) -> None:
    if not _has_table("mkt_daily_chance"):
        return
    rows = conn.execute(sa.text("SELECT * FROM mkt_daily_chance")).mappings().all()
    has_stock_table = _has_table("mkt_daily_chance_stock")
    for src in rows:
        plate_name = src.get("subject_name") or src.get("article_title") or ""
        values = {
            "trade_date": src["trade_date"],
            "plate_type": "chance",
            "platform": src.get("platform") or "cls",
            "rank_no": src.get("rank_no"),
            "plate_code": str(src.get("subject_id") or ""),
            "plate_name": plate_name,
            "change_pct": None,
            "raw_score": None,
            "limit_up_count": None,
            "up_reason": src.get("article_title") or plate_name,
            "source_update_time": src.get("source_update_time"),
            "collected_at": src.get("collected_at"),
            "created_at": src.get("created_at"),
            "updated_at": src.get("updated_at"),
        }
        plate_id = _upsert_plate(conn, plate_columns, values)
        if not plate_id or not has_stock_table:
            continue
        stocks = conn.execute(
            sa.text("SELECT * FROM mkt_daily_chance_stock WHERE chance_id=:chance_id"),
            {"chance_id": src["id"]},
        ).mappings().all()
        for stock in stocks:
            _insert_plate_stock(conn, stock_columns, plate_id, stock)


def _migrate_tuyeres(conn, plate_columns: set[str], stock_columns: set[str]) -> None:
    if not _has_table("mkt_daily_tuyere"):
        return
    rows = conn.execute(sa.text("SELECT * FROM mkt_daily_tuyere")).mappings().all()
    has_stock_table = _has_table("mkt_daily_tuyere_stock")
    for src in rows:
        plate_name = src.get("subject_name") or src.get("driver") or ""
        values = {
            "trade_date": src["trade_date"],
            "plate_type": "tuyere",
            "platform": src.get("platform") or "cls",
            "rank_no": src.get("rank_no"),
            "plate_code": str(src.get("subject_id") or ""),
            "plate_name": plate_name,
            "change_pct": None,
            "raw_score": None,
            "limit_up_count": None,
            "up_reason": src.get("driver") or plate_name,
            "source_update_time": src.get("source_update_time"),
            "collected_at": src.get("collected_at"),
            "created_at": src.get("created_at"),
            "updated_at": src.get("updated_at"),
        }
        plate_id = _upsert_plate(conn, plate_columns, values)
        if not plate_id or not has_stock_table:
            continue
        stocks = conn.execute(
            sa.text("SELECT * FROM mkt_daily_tuyere_stock WHERE tuyere_id=:tuyere_id"),
            {"tuyere_id": src["id"]},
        ).mappings().all()
        for stock in stocks:
            _insert_plate_stock(conn, stock_columns, plate_id, stock)


def _migrate_limit_up_plates(conn, plate_columns: set[str], stock_columns: set[str]) -> None:
    if not _has_table("mkt_limit_up_plate"):
        return
    rows = conn.execute(sa.text("SELECT * FROM mkt_limit_up_plate")).mappings().all()
    has_stock_table = _has_table("mkt_limit_up_stock")
    for src in rows:
        values = {
            "trade_date": src["trade_date"],
            "plate_type": "limit_up",
            "platform": src.get("platform") or "cls",
            "rank_no": None,
            "plate_code": src.get("plate_code") or "",
            "plate_name": src.get("plate_name") or "",
            "change_pct": src.get("change_pct"),
            "raw_score": src.get("limit_up_count"),
            "limit_up_count": src.get("limit_up_count"),
            "up_reason": src.get("up_reason") or "",
            "source_update_time": src.get("source_update_time"),
            "collected_at": src.get("collected_at"),
            "created_at": src.get("created_at"),
            "updated_at": src.get("updated_at"),
        }
        plate_id = _upsert_plate(conn, plate_columns, values)
        if not plate_id or not has_stock_table:
            continue
        stocks = conn.execute(
            sa.text(
                """
                SELECT stock_code, stock_name, change_pct, last_price
                FROM mkt_limit_up_stock
                WHERE trade_date=:trade_date AND platform=:platform AND plate_code=:plate_code
                """
            ),
            values,
        ).mappings().all()
        for stock in stocks:
            _insert_plate_stock(conn, stock_columns, plate_id, stock)


def upgrade() -> None:
    if not (_has_table("mkt_daily_plate") and _has_table("mkt_daily_plate_stock")):
        return
    conn = op.get_bind()
    plate_columns = _columns("mkt_daily_plate")
    stock_columns = _columns("mkt_daily_plate_stock")
    _migrate_chances(conn, plate_columns, stock_columns)
    _migrate_tuyeres(conn, plate_columns, stock_columns)
    _migrate_limit_up_plates(conn, plate_columns, stock_columns)


def downgrade() -> None:
    # Data-only migration. Keep copied records in place on downgrade.
    pass
