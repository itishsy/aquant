import pytest

from app.services.normalization import normalize_stock_code, xueqiu_link


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("600000", "600000.SH"),
        ("SH600000", "600000.SH"),
        ("600000.SH", "600000.SH"),
        ("000001", "000001.SZ"),
        ("SZ000001", "000001.SZ"),
        ("430000", "430000.BJ"),
    ],
)
def test_normalize_stock_code(raw, expected):
    assert normalize_stock_code(raw) == expected


def test_xueqiu_link():
    assert xueqiu_link("600000.SH") == "https://xueqiu.com/S/SH600000"
