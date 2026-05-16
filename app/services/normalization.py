from __future__ import annotations

import re


CODE_RE = re.compile(r"^(?:(SH|SZ|BJ))?(\d{6})(?:\.(SH|SZ|BJ))?$", re.IGNORECASE)


def normalize_stock_code(value: str) -> str:
    raw = value.strip().upper()
    match = CODE_RE.match(raw)
    if not match:
        raise ValueError("invalid stock code")
    prefix, code, suffix = match.groups()
    exchange = suffix or prefix
    if not exchange:
        if code.startswith(("60", "68")):
            exchange = "SH"
        elif code.startswith(("00", "30")):
            exchange = "SZ"
        elif code.startswith(("43", "83", "87")):
            exchange = "BJ"
        else:
            raise ValueError("cannot infer exchange")
    return f"{exchange.lower()}{code}"


def xueqiu_link(stock_code: str) -> str:
    normalized = normalize_stock_code(stock_code)
    return f"https://xueqiu.com/S/{normalized}"
