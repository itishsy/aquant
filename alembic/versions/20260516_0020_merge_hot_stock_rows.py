"""Merge duplicate hot-stock rows under the new single-row schema.

Revision ID: 20260516_0020
Revises: 20260516_0019
Create Date: 2026-05-16
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0020"
down_revision: str | None = "20260516_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _hot_code(value: Any) -> str:
    text = str(value or "").strip()
    lower = text.lower()
    if lower.startswith(("sh", "sz", "bj")):
        return lower
    if "." in text:
        code, market = text.split(".", 1)
        return f"{market.lower()}{code}"
    market = "sh" if text.startswith("6") else "bj" if text.startswith(("4", "8")) else "sz"
    return f"{market}{text}" if text else ""


def _append_text(existing: str, value: Any) -> str:
    parts = [part.strip() for part in str(existing or "").split("；") if part.strip()]
    for part in [p.strip() for p in str(value or "").replace(",", "；").split("；") if p.strip()]:
        if part not in parts:
            parts.append(part)
    return "；".join(parts)


def _score(cls_rank: int | None, ths_rank: int | None, tgb_rank: int | None) -> int:
    primes = {1: 71, 2: 67, 3: 61, 4: 59, 5: 53, 6: 47, 7: 43, 8: 41, 9: 37, 10: 31}
    return sum(primes.get(rank, 0) for rank in (cls_rank, ths_rank, tgb_rank) if rank and 1 <= rank <= 10)


def _insert(conn, columns: set[str], values: dict[str, Any]) -> None:
    payload = {key: value for key, value in values.items() if key in columns}
    sql_cols = ", ".join(payload.keys())
    sql_vals = ", ".join(f":{key}" for key in payload)
    conn.execute(sa.text(f"INSERT INTO mkt_hot_stock ({sql_cols}) VALUES ({sql_vals})"), payload)


def upgrade() -> None:
    if not _has_table("mkt_hot_stock"):
        return
    columns = _columns("mkt_hot_stock")
    required = {"trade_date", "stock_code", "stock_name", "price", "change_pct", "reason", "tag", "created_at"}
    if not required.issubset(columns):
        return

    conn = op.get_bind()
    rows = [dict(row) for row in conn.execute(sa.text("SELECT * FROM mkt_hot_stock ORDER BY trade_date, id")).mappings().all()]
    merged: dict[tuple[Any, str], dict[str, Any]] = {}
    for row in rows:
        code = _hot_code(row.get("stock_code"))
        if not code:
            continue
        key = (row.get("trade_date"), code)
        item = merged.setdefault(
            key,
            {
                "trade_date": row.get("trade_date"),
                "stock_code": code,
                "stock_name": row.get("stock_name") or "",
                "assoc_plate": "",
                "cls_rank": None,
                "ths_rank": None,
                "tgb_rank": None,
                "price": None,
                "change_pct": None,
                "reason": "",
                "score": None,
                "tag": "",
                "created_at": row.get("created_at") or datetime.utcnow(),
            },
        )
        item["stock_name"] = row.get("stock_name") or item["stock_name"]
        item["assoc_plate"] = _append_text(item["assoc_plate"], row.get("assoc_plate") or row.get("board_name"))
        item["reason"] = _append_text(item["reason"], row.get("reason") or row.get("raw_reason"))
        item["tag"] = _append_text(item["tag"], row.get("tag"))
        if row.get("price") is not None:
            item["price"] = row.get("price")
        if row.get("change_pct") is not None:
            item["change_pct"] = row.get("change_pct")
        for rank_key in ("cls_rank", "ths_rank", "tgb_rank"):
            if row.get(rank_key) is not None:
                item[rank_key] = row.get(rank_key)
        platform = str(row.get("platform") or "").lower()
        platform_rank = row.get("platform_rank")
        if platform_rank is not None:
            if platform in {"cls", "财联社", "platform_a"}:
                item["cls_rank"] = platform_rank
            elif platform in {"ths", "同花顺", "platform_b"}:
                item["ths_rank"] = platform_rank
            elif platform in {"tgb", "淘股吧", "东方财富", "platform_c"}:
                item["tgb_rank"] = platform_rank

    conn.execute(sa.text("DELETE FROM mkt_hot_stock"))
    for item in merged.values():
        if item["price"] is None or item["change_pct"] is None:
            continue
        item["assoc_plate"] = item["assoc_plate"] or "未匹配板块"
        item["reason"] = item["reason"] or item["assoc_plate"]
        item["tag"] = item["tag"] or ""
        item["score"] = _score(item["cls_rank"], item["ths_rank"], item["tgb_rank"])
        _insert(conn, columns, item)


def downgrade() -> None:
    # Data cleanup migration only.
    pass
