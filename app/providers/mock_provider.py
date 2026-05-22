from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.providers.base import (
    HotRankProvider,
    LimitUpProvider,
    MarketDataProvider,
    SectorDataProvider,
    TradingCalendarProvider,
)


class MockProvider(
    MarketDataProvider,
    HotRankProvider,
    LimitUpProvider,
    SectorDataProvider,
    TradingCalendarProvider,
):
    PRIME_SCORES = {
        1: 71,
        2: 67,
        3: 61,
        4: 59,
        5: 53,
        6: 47,
        7: 43,
        8: 41,
        9: 37,
        10: 31,
        11: 29,
        12: 23,
        13: 19,
        14: 17,
        15: 13,
        16: 11,
        17: 7,
        18: 5,
        19: 3,
        20: 2,
    }

    STOCKS = {
        "600000.SH": {"name": "浦发银行", "sector": "金融"},
        "000001.SZ": {"name": "平安银行", "sector": "金融"},
        "300750.SZ": {"name": "宁德时代", "sector": "新能源"},
        "002594.SZ": {"name": "比亚迪", "sector": "新能源"},
        "603019.SH": {"name": "中科曙光", "sector": "算力"},
        "002230.SZ": {"name": "科大讯飞", "sector": "AI应用"},
        "601127.SH": {"name": "赛力斯", "sector": "新能源"},
        "430000.BJ": {"name": "北交样本", "sector": "北交所"},
    }

    def get_market_snapshot(self, trade_date: date) -> dict:
        return {
            "trade_date": trade_date,
            "sh_index": 3128.2,
            "sz_index": 10122.5,
            "cyb_index": 2016.3,
            "total_amount": 11250.0,
            "up_count": 3412,
            "down_count": 1286,
            "flat_count": 102,
            "up_ratio": 0.70,
            "limit_up_count": 68,
            "limit_down_count": 3,
            "broken_limit_count": 9,
            "broken_limit_ratio": 0.12,
            "max_continue_board": 4,
            "yesterday_limit_avg_return": 2.8,
            "north_money": 25.6,
            "market_comment": "指数温和反弹，情绪修复，仍需注意分化。",
        }

    def get_sector_daily(self, trade_date: date) -> list[dict]:
        return [
            {
                "trade_date": trade_date,
                "sector_name": "新能源",
                "change_pct": 3.8,
                "limit_up_count": 8,
                "leader_stock_code": "300750.SZ",
                "leader_stock_name": "宁德时代",
                "leader_board_count": 2,
                "fund_strength": 88,
                "continuity_days": 3,
                "heat_spread": 82,
            },
            {
                "trade_date": trade_date,
                "sector_name": "算力",
                "change_pct": 2.7,
                "limit_up_count": 5,
                "leader_stock_code": "603019.SH",
                "leader_stock_name": "中科曙光",
                "leader_board_count": 1,
                "fund_strength": 79,
                "continuity_days": 2,
                "heat_spread": 77,
            },
            {
                "trade_date": trade_date,
                "sector_name": "AI应用",
                "change_pct": 1.9,
                "limit_up_count": 3,
                "leader_stock_code": "002230.SZ",
                "leader_stock_name": "科大讯飞",
                "leader_board_count": 1,
                "fund_strength": 73,
                "continuity_days": 1,
                "heat_spread": 70,
            },
            {
                "trade_date": trade_date,
                "sector_name": "金融",
                "change_pct": -1.2,
                "limit_up_count": 0,
                "leader_stock_code": "600000.SH",
                "leader_stock_name": "浦发银行",
                "leader_board_count": 0,
                "fund_strength": 30,
                "continuity_days": 0,
                "heat_spread": 25,
            },
        ]

    def get_hot_stock_rank(self, trade_date: date) -> list[dict]:
        rows = []
        platforms = ["platform_a", "platform_b", "platform_c"]
        mapping = {
            "platform_a": ["300750.SZ", "603019.SH", "002230.SZ", "002594.SZ", "601127.SH"],
            "platform_b": ["300750.SZ", "002594.SZ", "603019.SH", "002230.SZ", "600000.SH"],
            "platform_c": ["603019.SH", "300750.SZ", "002230.SZ", "601127.SH", "430000.BJ"],
        }
        for platform in platforms:
            for idx, stock_code in enumerate(mapping[platform], start=1):
                stock = self.STOCKS[stock_code]
                hot_code = stock_code.split(".")[-1].lower() + stock_code.split(".")[0] if "." in stock_code else stock_code.lower()
                rows.append(
                    {
                        "trade_date": trade_date,
                        "platform": platform,
                        "rank_field": {"platform_a": "cls_rank", "platform_b": "ths_rank", "platform_c": "tgb_rank"}[platform],
                        "rank": idx,
                        "stock_code": hot_code,
                        "stock_name": stock["name"],
                        "assoc_plate": stock["sector"],
                        "reason": f"{stock['sector']} mock reason",
                        "tag": stock["sector"],
                        "price": 10 + idx,
                        "change_pct": 1.5 + idx / 10,
                    }
                )
        return rows

    def get_stock_quote(self, stock_code: str) -> dict[str, float | None]:
        text = str(stock_code or "").strip().upper()
        if text.startswith(("SH", "SZ", "BJ")) and len(text) == 8:
            key = f"{text[2:]}.{text[:2]}"
        else:
            key = text
        codes = list(self.STOCKS)
        try:
            idx = codes.index(key) + 1
        except ValueError:
            idx = 1
        return {"price": round(10 + idx, 2), "change_pct": round(1.5 + idx / 10, 2)}

    def get_limit_up_list(self, trade_date: date) -> list[dict]:
        return [
            {
                "trade_date": trade_date,
                "stock_code": "002594.SZ",
                "stock_name": "比亚迪",
                "limit_time": "10:02",
                "open_limit_count": 0,
                "seal_amount": 4.2,
                "seal_volume": 180000,
                "turnover_rate": 8.5,
                "amount": 95.2,
                "board_count": 2,
                "concept": "新能源车",
                "reason": "板块共振",
                "is_first_board": False,
                "is_continue_board": True,
                "risk_flag": "",
            },
            {
                "trade_date": trade_date,
                "stock_code": "601127.SH",
                "stock_name": "赛力斯",
                "limit_time": "13:20",
                "open_limit_count": 1,
                "seal_amount": 2.1,
                "seal_volume": 90000,
                "turnover_rate": 12.2,
                "amount": 83.4,
                "board_count": 1,
                "concept": "新能源车",
                "reason": "主线扩散",
                "is_first_board": True,
                "is_continue_board": False,
                "risk_flag": "炸板回封",
            },
        ]

    def get_daily_kline(self, stock_code: str, start_date: date, end_date: date) -> list[dict]:
        days = []
        base = 20.0 if stock_code != "600000.SH" else 10.0
        cur = start_date
        step = 0
        while cur <= end_date:
            close = round(base + step * 0.25 + ((step % 3) - 1) * 0.1, 2)
            prev_close = round(close - 0.18, 2)
            days.append(
                {
                    "stock_code": stock_code,
                    "trade_date": cur,
                    "open": round(close - 0.1, 2),
                    "high": round(close + 0.3, 2),
                    "low": round(close - 0.35, 2),
                    "close": close,
                    "prev_close": prev_close,
                    "volume": 1000000 + step * 50000,
                    "amount": (1000000 + step * 50000) * close / 10000,
                    "change_pct": round((close - prev_close) / prev_close * 100, 2),
                }
            )
            cur += timedelta(days=1)
            step += 1
        return days

    def get_intraday_kline(
        self, stock_code: str, interval: str, start_time: datetime, end_time: datetime
    ) -> list[dict]:
        if stock_code == "603019.SH":
            closes = [25.8, 25.4, 25.0, 24.8, 24.6, 24.55, 24.62, 24.74, 24.88, 25.05]
            macd_support = [0.0, -0.12, -0.18, -0.22, -0.16, -0.1, -0.04, 0.03, 0.08, 0.12]
        else:
            closes = [18.5, 18.7, 18.6, 18.9, 19.0, 19.1, 19.2, 19.3]
            macd_support = [0.02] * len(closes)

        result = []
        current = datetime.combine(start_time.date(), time(9, 30))
        for idx, close in enumerate(closes):
            prev_close = closes[idx - 1] if idx > 0 else close + 0.1
            result.append(
                {
                    "stock_code": stock_code,
                    "trade_time": current,
                    "open": round(close - 0.08, 2),
                    "high": round(close + 0.12, 2),
                    "low": round(close - 0.15, 2),
                    "close": close,
                    "prev_close": round(prev_close, 2),
                    "volume": 10000 - idx * 350 if stock_code == "603019.SH" else 12000 + idx * 180,
                    "amount": (10000 - idx * 350 if stock_code == "603019.SH" else 12000 + idx * 180)
                    * close
                    / 10000,
                    "change_pct": round((close - prev_close) / prev_close * 100, 2),
                    "mock_macd_hint": macd_support[idx],
                }
            )
            current += timedelta(minutes=15)
            if current > end_time:
                break
        return result

    def is_trade_day(self, day: date) -> bool:
        return day.weekday() < 5

    def previous_trade_day(self, day: date) -> date:
        previous = day - timedelta(days=1)
        while previous.weekday() >= 5:
            previous -= timedelta(days=1)
        return previous
