import pytest

from app.services.normalization import normalize_stock_code, xueqiu_link


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("600000", "sh600000"),
        ("SH600000", "sh600000"),
        ("600000.SH", "sh600000"),
        ("000001", "sz000001"),
        ("SZ000001", "sz000001"),
        ("430000", "bj430000"),
    ],
)
def test_normalize_stock_code(raw, expected):
    assert normalize_stock_code(raw) == expected


def test_xueqiu_link():
    assert xueqiu_link("600000.SH") == "https://xueqiu.com/S/sh600000"
