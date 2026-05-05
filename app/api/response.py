from __future__ import annotations

from uuid import uuid4


def ok(data=None, message: str = "操作成功"):
    return {
        "success": True,
        "code": "SUCCESS",
        "message": message,
        "data": data if data is not None else {},
        "trace_id": f"req_{uuid4().hex[:12]}",
    }


def page(items: list, page_no: int = 1, page_size: int = 20, total: int | None = None):
    return {
        "list": items,
        "page_no": page_no,
        "page_size": page_size,
        "total": len(items) if total is None else total,
    }
