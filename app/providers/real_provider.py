from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from app.providers.base import (
    HotRankProvider,
    LimitUpProvider,
    MarketDataProvider,
    SectorDataProvider,
    TradingCalendarProvider,
)
from app.providers.mock_provider import MockProvider
from app.services.normalization import normalize_stock_code


class RealMarketProvider(
    MarketDataProvider,
    HotRankProvider,
    LimitUpProvider,
    SectorDataProvider,
    TradingCalendarProvider,
):
    """Public JSON provider based on the existing fupan implementation.

    The provider intentionally avoids browser automation, account login, broker
    integration, and anti-bot bypass behavior. If upstream JSON endpoints fail,
    callers receive an exception and task logging records the failure.
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    def __init__(self) -> None:
        self.client = httpx.Client(headers=self.HEADERS, timeout=20, follow_redirects=True)

    def _get_json(self, url: str, data_key: str = "data", referer: str | None = None) -> Any:
        headers = {"Referer": referer} if referer else None
        response = self.client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
        if data_key == "":
            return payload
        return payload[data_key]

    @staticmethod
    def _number(value: Any, default: float = 0.0) -> float:
        if value is None or value == "":
            return default
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).replace(",", "").strip()
        multiplier = 1.0
        if "万亿" in text:
            multiplier = 10000.0
        elif "亿" in text:
            multiplier = 1.0
        elif "万" in text:
            multiplier = 0.0001
        cleaned = "".join(ch for ch in text if ch.isdigit() or ch in ".-")
        return float(cleaned) * multiplier if cleaned else default

    @staticmethod
    def _pct(value: Any) -> float:
        number = RealMarketProvider._number(value)
        return round(number * 100, 2) if abs(number) <= 1 else round(number, 2)

    @staticmethod
    def _index_change_pct(item: dict[str, Any]) -> float:
        return RealMarketProvider._pct(item.get("change"))

    @staticmethod
    def _index_change_px(item: dict[str, Any]) -> float:
        return round(RealMarketProvider._number(item.get("change_px")), 2)

    @staticmethod
    def _int(value: Any, default: int = 0) -> int:
        if value is None or value == "":
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        text = str(value)
        if "板" in text:
            before_board = text.split("板", 1)[0]
            matches = re.findall(r"\d+", before_board)
            return int(matches[-1]) if matches else default
        matches = re.findall(r"\d+", text)
        return int(matches[0]) if matches else default

    @staticmethod
    def _to_code(raw: str) -> str:
        text = raw.strip()
        if text.lower().startswith(("sh", "sz", "bj")):
            return normalize_stock_code(text[:2].upper() + text[2:])
        return normalize_stock_code(text)

    @staticmethod
    def _eastmoney_secid(stock_code: str) -> str:
        code, exchange = normalize_stock_code(stock_code).split(".")
        market = {"SH": "1", "SZ": "0", "BJ": "0"}[exchange]
        return f"{market}.{code}"

    @staticmethod
    def _cls_secu_code(stock_code: str) -> str:
        code, exchange = normalize_stock_code(stock_code).split(".")
        return f"{exchange.lower()}{code}"

    @staticmethod
    def _simplify_cls_stock(item: dict[str, Any]) -> dict:
        return {
            "stock_name": item.get("name") or "",
            "stock_code": item.get("StockID") or "",
            "change_pct": RealMarketProvider._pct(item.get("RiseRange")),
            "last_price": RealMarketProvider._number(item.get("last")),
        }

    def _simplify_cls_subject(self, item: dict[str, Any], kind: str) -> dict:
        return {
            "source": "cls",
            "kind": kind,
            "subject_id": item.get("subject_id"),
            "subject_name": item.get("subject_name") or "",
            "title": item.get("article_name") or item.get("driver") or "",
            "driver": item.get("driver") or "",
            "article_id": item.get("article_id"),
            "article_time": item.get("article_time"),
            "attention_num": item.get("attention_num"),
            "stocks": [self._simplify_cls_stock(stock) for stock in item.get("stock_list") or item.get("stocks") or []],
        }

    @staticmethod
    def _simplify_ths_stock(item: dict[str, Any]) -> dict:
        return {
            "stock_name": item.get("name") or "",
            "stock_code": item.get("code") or "",
            "change_pct": RealMarketProvider._pct(item.get("rise_and_fall")),
        }

    def _simplify_ths_topic(self, item: dict[str, Any], rank_no: int) -> dict:
        attach_info = item.get("attach_info") or {}
        stocks = attach_info.get("att_stock") or item.get("attach_hot_stock") or []
        return {
            "source": "ths",
            "rank_no": rank_no,
            "topic_code": item.get("code"),
            "title": item.get("title") or "",
            "description": item.get("description") or "",
            "subtitle": item.get("subtitle") or "",
            "hot_value": item.get("hot_value"),
            "jump_url": item.get("jump_url"),
            "stocks": [self._simplify_ths_stock(stock) for stock in stocks],
        }

    def _get_market_subjects(self) -> dict:
        cls_payload = self._get_json(
            "https://www.cls.cn/api/subject/recommend/article"
            "?app=CailianpressWeb&os=web&sv=8.4.6"
            "&sign=9f8797a1f4de66c2370f7a03990d2737",
            referer="https://www.cls.cn/",
        )
        ths_payload = self._get_json(
            "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/topic?page=1&page_size=10",
            referer="https://dq.10jqka.com.cn/",
        )
        return {
            "today_chances": [
                self._simplify_cls_subject(item, "today_chance")
                for item in (cls_payload.get("today_chances") or [])
            ],
            "today_tuyeres": [
                self._simplify_cls_subject(item, "today_tuyere")
                for item in (cls_payload.get("today_tuyeres") or [])
            ],
            "topic_list": [
                self._simplify_ths_topic(item, rank_no)
                for rank_no, item in enumerate((ths_payload.get("topic_list") or [])[:5], start=1)
            ],
            "raw_market_subjects": {"cls": cls_payload, "ths": ths_payload},
        }

    def _simplify_continuous_limit_stock(self, item: dict[str, Any]) -> dict:
        raw_code = item.get("secu_code") or ""
        try:
            stock_code = self._to_code(raw_code)
        except Exception:
            stock_code = raw_code
        return {
            "stock_code": stock_code,
            "stock_name": item.get("secu_name") or "",
        }

    def _simplify_limit_up_ladder(self, analysis: dict[str, Any]) -> list[dict]:
        rows = []
        for item in analysis.get("continuous_limit_up") or []:
            stocks = [self._simplify_continuous_limit_stock(stock) for stock in item.get("stock_list") or []]
            rows.append(
                {
                    "height": self._int(item.get("height")),
                    "count": len(stocks),
                    "stocks": stocks,
                }
            )
        return sorted(rows, key=lambda row: row["height"], reverse=True)

    @staticmethod
    def _parse_limit_up_text(text: Any) -> tuple[int | None, int]:
        value = str(text or "").strip()
        if not value:
            return None, 1
        numbers = [int(item) for item in re.findall(r"\d+", value)]
        if len(numbers) >= 2:
            return numbers[0], numbers[1]
        if len(numbers) == 1:
            return None, numbers[0]
        return None, 1

    @staticmethod
    def _parse_cls_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        text = str(value).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    def get_limit_up_analysis(self, trade_date: date) -> dict:
        payload = self._get_json(
            "https://x-quote.cls.cn/v2/quote/a/plate/up_down_analysis",
            referer="https://www.cls.cn/",
        )
        ladder_rows = self._simplify_limit_up_ladder(payload)
        ladder_by_code: dict[str, int] = {}
        for ladder in ladder_rows:
            for stock in ladder.get("stocks") or []:
                ladder_by_code[stock.get("stock_code", "")] = ladder["height"]

        plate_rows = []
        stock_rows_by_code: dict[str, dict] = {}
        for plate in payload.get("plate_stock") or []:
            plate_code = plate.get("secu_code") or ""
            plate_name = plate.get("secu_name") or ""
            plate_rows.append(
                {
                    "trade_date": trade_date,
                    "source": "real",
                    "platform": "cls",
                    "plate_code": plate_code,
                    "plate_name": plate_name,
                    "change_pct": self._pct(plate.get("change")),
                    "limit_up_count": self._int(plate.get("plate_stock_up_num")),
                    "up_reason": plate.get("up_reason") or "",
                }
            )
            for stock in plate.get("stock_list") or []:
                try:
                    stock_code = self._to_code(stock.get("secu_code", ""))
                except Exception:
                    continue
                if stock_code in stock_rows_by_code:
                    continue
                up_reason = stock.get("up_reason") or ""
                reason_tags = ",".join(stock.get("up_tags") or [])
                if not reason_tags and "|" in up_reason:
                    reason_tags = up_reason.split("|", 1)[0]
                board_days, board_count = self._parse_limit_up_text(stock.get("up_num"))
                stock_rows_by_code[stock_code] = {
                    "trade_date": trade_date,
                    "source": "real",
                    "platform": "cls",
                    "raw_secu_code": stock.get("secu_code") or "",
                    "stock_code": stock_code,
                    "stock_name": stock.get("secu_name") or "",
                    "plate_code": plate_code,
                    "plate_name": plate_name,
                    "change_pct": self._pct(stock.get("change")),
                    "last_price": self._number(stock.get("last_px")),
                    "circulating_market_cap": self._number(stock.get("cmc")),
                    "limit_time": stock.get("time") or "",
                    "limit_datetime": self._parse_cls_datetime(stock.get("time")),
                    "board_days": board_days,
                    "board_count": board_count,
                    "board_text": stock.get("up_num") or "",
                    "limit_reason": up_reason,
                    "reason_tags": reason_tags,
                    "ladder_height": ladder_by_code.get(stock_code),
                }
        return {
            "trade_date": trade_date,
            "ladders": ladder_rows,
            "plates": plate_rows,
            "stocks": list(stock_rows_by_code.values()),
        }

    def get_market_snapshot(self, trade_date: date) -> dict:
        index_data = self._get_json(
            "https://x-quote.cls.cn/v2/quote/a/web/stocks/basic"
            "?app=CailianpressWeb&fields=secu_name,secu_code,trade_status,change,change_px,last_px"
            "&os=web&secu_codes=sh000001,sz399001,sz399006&sv=8.4.6"
            "&sign=7ddfd2eef7564087ff01a1782c724f43",
            referer="https://www.cls.cn/",
        )
        emotion = self._get_json(
            "https://x-quote.cls.cn/v2/quote/a/stock/emotion"
            "?app=CailianpressWeb&os=web&sv=8.4.6&sign=9f8797a1f4de66c2370f7a03990d2737",
            referer="https://www.cls.cn/",
        )
        analysis = self._get_json(
            "https://x-quote.cls.cn/v2/quote/a/plate/up_down_analysis",
            referer="https://www.cls.cn/",
        )
        market_subjects = self._get_market_subjects()

        up_down = emotion.get("up_down_dis", {})
        sh_index = index_data.get("sh000001", {}) or {}
        sz_index = index_data.get("sz399001", {}) or {}
        cyb_index = index_data.get("sz399006", {}) or {}
        up_count = int(up_down.get("rise_num") or 0)
        down_count = int(up_down.get("fall_num") or up_down.get("down_num") or 0)
        flat_count = int(up_down.get("flat_num") or 0)
        total = up_count + down_count + flat_count
        continuous = analysis.get("continuous_limit_up", []) or []
        broken = int(emotion.get("open_board_num") or emotion.get("炸板数") or 0)
        limit_up = int(emotion.get("up_ratio_num") or emotion.get("zt_num") or 0)
        return {
            "trade_date": trade_date,
            "sh_index": round(self._number(sh_index.get("last_px")), 2),
            "sz_index": round(self._number(sz_index.get("last_px")), 2),
            "cyb_index": round(self._number(cyb_index.get("last_px")), 2),
            "index_change_pct": self._index_change_pct(sh_index),
            "sh_index_change_pct": self._index_change_pct(sh_index),
            "sh_index_change_px": self._index_change_px(sh_index),
            "sz_index_change_pct": self._index_change_pct(sz_index),
            "sz_index_change_px": self._index_change_px(sz_index),
            "cyb_index_change_pct": self._index_change_pct(cyb_index),
            "cyb_index_change_px": self._index_change_px(cyb_index),
            "index_trade_status": {
                "sh000001": sh_index.get("trade_status"),
                "sz399001": sz_index.get("trade_status"),
                "sz399006": cyb_index.get("trade_status"),
            },
            "today_chances": market_subjects["today_chances"],
            "today_tuyeres": market_subjects["today_tuyeres"],
            "topic_list": market_subjects["topic_list"],
            "limit_up_ladder": self._simplify_limit_up_ladder(analysis),
            "total_amount": round(self._number(emotion.get("shsz_balance")), 2),
            "up_count": up_count,
            "down_count": down_count,
            "flat_count": flat_count,
            "up_ratio": round(up_count / total, 4) if total else 0,
            "limit_up_count": limit_up,
            "limit_down_count": int(up_down.get("down_num") or emotion.get("down_ratio_num") or 0),
            "broken_limit_count": broken,
            "broken_limit_ratio": round(broken / limit_up, 4) if limit_up else 0,
            "max_continue_board": int(continuous[0].get("height") if continuous else 0),
            "yesterday_limit_avg_return": self._pct(emotion.get("yesterday_limit_avg_return")),
            "north_money": self._number(emotion.get("north_money")),
            "source_url": (
                "https://x-quote.cls.cn/v2/quote/a/web/stocks/basic"
                "?app=CailianpressWeb&fields=secu_name,secu_code,trade_status,change,change_px,last_px"
                "&os=web&secu_codes=sh000001,sz399001,sz399006&sv=8.4.6"
                "&sign=7ddfd2eef7564087ff01a1782c724f43"
            ),
            "raw_snapshot": {
                "index_data": index_data,
                "emotion": emotion,
                "analysis": analysis,
                "market_subjects": market_subjects["raw_market_subjects"],
            },
            "market_comment": "真实行情采集：市场状态仅作为交易辅助。",
        }

    def get_sector_daily(self, trade_date: date) -> list[dict]:
        payload = self._get_json(
            "https://x-quote.cls.cn/web_quote/plate/plate_list"
            "?app=CailianpressWeb&os=web&page=1&rever=1&sv=8.4.6&type=industry&way=change"
            "&sign=ef1ec7886be706a0b722d7e7bf3c0054",
            referer="https://www.cls.cn/",
        )
        items = payload.get("plate_data") or payload.get("data") or payload.get("plate_list") or []
        rows = []
        for idx, item in enumerate(items[:20], start=1):
            name = item.get("secu_name") or item.get("plate_name") or item.get("name") or f"板块{idx}"
            change_pct = self._pct(item.get("change"))
            rows.append(
                {
                    "trade_date": trade_date,
                    "sector_name": name,
                    "change_pct": change_pct,
                    "limit_up_count": int(item.get("limit_up_num") or item.get("up_num") or 0),
                    "leader_stock_code": None,
                    "leader_stock_name": item.get("leader_stock_name") or item.get("lead_stock_name"),
                    "leader_board_count": int(item.get("height") or 0),
                    "fund_strength": max(min(50 + change_pct * 10, 100), 0),
                    "continuity_days": 1 if change_pct > 0 else 0,
                    "heat_spread": max(min(50 + change_pct * 8, 100), 0),
                }
            )
        return rows

    def get_hot_stock_rank(self, trade_date: date) -> list[dict]:
        rows: list[dict] = []
        self._append_cls_hot(rows, trade_date)
        self._append_ths_hot(rows, trade_date)
        self._append_tgb_hot(rows, trade_date)
        return rows

    def _append_hot(
        self,
        rows: list[dict],
        trade_date: date,
        platform: str,
        rank: int,
        raw_code: str,
        name: str,
        sector: str = "",
        raw_payload: dict | None = None,
        price: float | None = None,
        change_pct: float | None = None,
    ) -> None:
        if rank > 20:
            return
        stock_code = self._to_code(raw_code)
        if stock_code.split(".")[0].startswith(("8", "4")):
            return
        rows.append(
            {
                "trade_date": trade_date,
                "platform": platform,
                "platform_rank": rank,
                "stock_code": stock_code,
                "stock_name": name,
                "sector_name": sector,
                "rank_score": MockProvider.PRIME_SCORES.get(rank, 1),
                "price": price,
                "change_pct": change_pct,
                "raw_payload": raw_payload or {},
            }
        )

    def _append_cls_hot(self, rows: list[dict], trade_date: date) -> None:
        items = self._get_json(
            "https://api3.cls.cn/v1/hot_stock?app=cailianpress&os=ios&sv=800"
            "&sign=f7f970ee36fc102317eeea2e5a6eb178",
            referer="https://www.cls.cn/",
        )
        for idx, item in enumerate(items[:20], start=1):
            stock = item.get("stock", {})
            stock_id = stock.get("StockID") or stock.get("stock_id") or ""
            if len(stock_id) >= 8:
                price = stock.get("last") or stock.get("Last") or stock.get("last_px")
                change = stock.get("RiseRange") or stock.get("change") or stock.get("change_pct")
                self._append_hot(rows, trade_date, "cls", idx, stock_id, stock.get("name", ""),
                    raw_payload=item,
                    price=float(price) if price else None,
                    change_pct=float(change) if change else None)

    def _append_ths_hot(self, rows: list[dict], trade_date: date) -> None:
        payload = self._get_json(
            "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock"
            "?stock_type=a&type=day&list_type=normal",
            referer="https://dq.10jqka.com.cn/",
        )
        items = payload.get("stock_list", [])
        for idx, item in enumerate(items[:20], start=1):
            tag = item.get("tag", {}) or {}
            sector = ",".join(tag.get("concept_tag", []) or [])
            price = item.get("price") or item.get("last_price")
            change = item.get("change") or item.get("change_pct")
            self._append_hot(
                rows, trade_date, "ths", idx,
                item.get("code", ""), item.get("name", ""),
                sector=sector, raw_payload=item,
                price=float(price) if price else None,
                change_pct=float(change) if change else None)

    def _append_tgb_hot(self, rows: list[dict], trade_date: date) -> None:
        items = self._get_json(
            "https://www.taoguba.com.cn/new/nrnt/getNoticeStock?type=D",
            data_key="dto",
            referer="https://www.taoguba.com.cn/",
        )
        for idx, item in enumerate(items[:20], start=1):
            full_code = item.get("fullCode", "")
            concepts = ",".join(gn.get("gnName", "") for gn in item.get("gnList", []) if gn.get("gnName"))
            if len(full_code) >= 8:
                self._append_hot(
                    rows,
                    trade_date,
                    "tgb",
                    idx,
                    full_code,
                    item.get("stockName", ""),
                    sector=concepts,
                    raw_payload=item,
                )

    def get_limit_up_list(self, trade_date: date) -> list[dict]:
        payload = self._get_json(
            "https://x-quote.cls.cn/v2/quote/a/plate/up_down_analysis",
            referer="https://www.cls.cn/",
        )
        rows = []
        seen: set[str] = set()
        for plate in payload.get("plate_stock", []):
            concept = plate.get("secu_name", "")
            if "ST" in concept:
                continue
            for stock in plate.get("stock_list", []):
                stock_code = self._to_code(stock.get("secu_code", ""))
                if stock_code in seen:
                    continue
                seen.add(stock_code)
                reason_parts = (stock.get("up_reason") or "").split("|", 1)
                board_count = self._int(stock.get("up_num") or stock.get("continue_board_num"), default=1)
                rows.append(
                    {
                        "trade_date": trade_date,
                        "stock_code": stock_code,
                        "stock_name": stock.get("secu_name", ""),
                        "limit_time": str(stock.get("time", "")).split(" ")[-1][:5] or "00:00",
                        "open_limit_count": self._int(stock.get("open_num"), default=0),
                        "seal_amount": round(self._number(stock.get("seal_amount")) / 100000000, 2),
                        "seal_volume": self._number(stock.get("seal_volume")),
                        "turnover_rate": self._pct(stock.get("turnover_rate")),
                        "amount": round(self._number(stock.get("amount")) / 100000000, 2),
                        "board_count": board_count,
                        "concept": concept,
                        "reason": reason_parts[0],
                        "is_first_board": board_count == 1,
                        "is_continue_board": board_count >= 2,
                        "risk_flag": "炸板回封" if stock.get("open_num") else "",
                    }
                )
        return rows

    def get_market_review_snapshot(self, trade_date: date) -> dict:
        subject_payload = self._safe_json(
            "https://www.cls.cn/api/subject/recommend/article"
            "?app=CailianpressWeb&os=web&sv=8.4.6&sign=9f8797a1f4de66c2370f7a03990d2737",
            referer="https://www.cls.cn/",
        )
        topic_payload = self._safe_json(
            "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/topic?page=1&page_size=10",
            referer="https://dq.10jqka.com.cn/",
        )
        plate_payload = self._safe_json(
            "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/plate?type=concept",
            referer="https://dq.10jqka.com.cn/",
        )
        fund_payload = self._safe_json(
            "https://x-quote.cls.cn/web_quote/plate/plate_list"
            "?app=CailianpressWeb&os=web&page=1&rever=1&sv=8.4.6&type=industry&way=change"
            "&sign=ef1ec7886be706a0b722d7e7bf3c0054",
            referer="https://www.cls.cn/",
        )
        return {
            "trade_date": trade_date,
            "review_text": "真实复盘信息采集，仅作为交易辅助。",
            "concept": "",
            "chance": self._format_subject_items(subject_payload.get("today_chances", []), "stock_list", "article_name"),
            "tuyere": self._format_subject_items(subject_payload.get("today_tuyeres", []), "stocks", "driver"),
            "topic": self._format_topic_items(topic_payload.get("topic_list", [])),
            "subject": self._format_plate_items(plate_payload.get("plate_list", [])),
            "fund": self._format_fund_snapshot(fund_payload),
            "latent": self._format_latent_items(subject_payload.get("short_latents", [])),
            "raw_snapshot": {
                "subject": subject_payload,
                "topic": topic_payload,
                "plate": plate_payload,
                "fund": fund_payload,
            },
        }

    def _safe_json(self, url: str, data_key: str = "data", referer: str | None = None) -> dict:
        try:
            payload = self._get_json(url, data_key=data_key, referer=referer)
            return payload if isinstance(payload, dict) else {"items": payload}
        except Exception as exc:
            return {"error": str(exc)}

    @staticmethod
    def _format_stock_refs(stocks: list[dict]) -> list[dict]:
        refs = []
        for stock in stocks[:5]:
            raw_code = stock.get("StockID") or stock.get("code") or stock.get("secu_code") or ""
            try:
                code = RealMarketProvider._to_code(raw_code)
            except Exception:
                code = raw_code
            refs.append(
                {
                    "stock_code": code,
                    "stock_name": stock.get("name") or stock.get("secu_name") or "",
                    "last": stock.get("last") or stock.get("last_px"),
                    "change": stock.get("RiseRange") or stock.get("change"),
                }
            )
        return refs

    @staticmethod
    def _format_subject_items(items: list[dict], stocks_key: str, detail_key: str) -> list[dict]:
        return [
            {
                "name": item.get("subject_name", ""),
                "description": item.get(detail_key, ""),
                "stocks": RealMarketProvider._format_stock_refs(item.get(stocks_key, []) or []),
            }
            for item in items[:5]
        ]

    @staticmethod
    def _format_topic_items(items: list[dict]) -> list[dict]:
        return [
            {
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "heat": item.get("heat") or item.get("hot_value"),
            }
            for item in items[:8]
        ]

    @staticmethod
    def _format_plate_items(items: list[dict]) -> list[dict]:
        return [
            {
                "name": item.get("name", ""),
                "tag": item.get("hot_tag") or item.get("tag") or "",
                "description": item.get("description", ""),
            }
            for item in items[:8]
        ]

    @staticmethod
    def _format_latent_items(items: list[dict]) -> list[dict]:
        return [
            {
                "name": item.get("subject_name", ""),
                "description": item.get("subject_description", ""),
            }
            for item in items[:5]
        ]

    @staticmethod
    def _format_fund_snapshot(payload: dict) -> dict:
        main_fund = payload.get("main_fund_diff", {}) if isinstance(payload, dict) else {}
        return {
            "top_inflow": main_fund.get("top_main_fund_diff", [])[:5],
            "top_outflow": main_fund.get("last_main_fund_diff", [])[:5],
        }

    def get_daily_kline(self, stock_code: str, start_date: date, end_date: date) -> list[dict]:
        secu_code = self._cls_secu_code(stock_code)
        payload = self._get_json(
            "https://x-quote.cls.cn/quote/stock/kline"
            f"?limit=100&secu_code={secu_code}&type=fd1",
            referer="https://www.cls.cn/",
        )
        rows = []
        for item in payload or []:
            raw_date = str(item.get("date") or "")
            if len(raw_date) != 8:
                continue
            trade_date = datetime.strptime(raw_date, "%Y%m%d").date()
            if trade_date < start_date or trade_date > end_date:
                continue
            close = self._number(item.get("close_px"))
            rows.append(
                {
                    "stock_code": normalize_stock_code(stock_code),
                    "trade_date": trade_date,
                    "open": self._number(item.get("open_px")),
                    "close": close,
                    "high": self._number(item.get("high_px")),
                    "low": self._number(item.get("low_px")),
                    "volume": self._number(item.get("business_amount")),
                    "amount": self._number(item.get("business_balance")) / 10000,
                    "change_pct": self._pct(item.get("change")),
                    "prev_close": self._number(item.get("preclose_px")),
                    "ma5": self._number(item.get("ma5"), default=0.0) or None,
                    "ma10": self._number(item.get("ma10"), default=0.0) or None,
                    "ma20": self._number(item.get("ma20"), default=0.0) or None,
                    "source": "cls",
                    "source_update_time": datetime.utcnow(),
                }
            )
        return rows

    def get_intraday_kline(
        self, stock_code: str, interval: str, start_time: datetime, end_time: datetime
    ) -> list[dict]:
        secid = self._eastmoney_secid(stock_code)
        payload = self._get_json(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get"
            f"?secid={secid}&fields1=f1,f2,f3,f4,f5,f6"
            "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            f"&klt=15&fqt=1&beg={start_time:%Y%m%d}&end={end_time:%Y%m%d}",
            data_key="data",
            referer="https://quote.eastmoney.com/",
        )
        rows = []
        previous_close = 0.0
        for item in payload.get("klines", []) or []:
            parts = item.split(",")
            if len(parts) < 11:
                continue
            trade_time = datetime.strptime(parts[0], "%Y-%m-%d %H:%M")
            if not (start_time <= trade_time <= end_time):
                continue
            close = self._number(parts[2])
            prev_close = previous_close or self._number(parts[1])
            previous_close = close
            rows.append(
                {
                    "stock_code": normalize_stock_code(stock_code),
                    "trade_time": trade_time,
                    "open": self._number(parts[1]),
                    "close": close,
                    "high": self._number(parts[3]),
                    "low": self._number(parts[4]),
                    "volume": self._number(parts[5]),
                    "amount": self._number(parts[6]) / 10000,
                    "change_pct": self._number(parts[8]),
                    "prev_close": prev_close,
                }
            )
        return rows

    def is_trade_day(self, day: date) -> bool:
        return day.weekday() < 5

    def previous_trade_day(self, day: date) -> date:
        previous = day - timedelta(days=1)
        while previous.weekday() >= 5:
            previous -= timedelta(days=1)
        return previous
