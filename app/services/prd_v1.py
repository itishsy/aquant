from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import (
    ConfigDictionary,
    ConfigNotificationTemplate,
    ConfigOperationLog,
    ConfigReviewTemplate,
    ConfigStrategy,
    ConfigTask,
    MktDaily,
    MktDailyChance,
    MktDailyChanceStock,
    MktDailyTopic,
    MktDailyTopicStock,
    MktDailyTuyere,
    MktDailyTuyereStock,
    MktHotBoard,
    MktHotStock,
    MktLimitUp,
    MktLimitUpLadder,
    MktLimitUpLadderStock,
    MktLimitUpStock,
    MyNotificationSetting,
    MyUserProfile,
    WatchPool,
    WatchPoolStatusLog,
)
from app.services.normalization import normalize_stock_code, xueqiu_link


ASSISTANT_NOTE = "仅作为交易辅助，请结合个人交易规则确认。"


class SeedService:
    DICTS = {
        "watch_tag": ["人气", "接力", "趋势"],
        "operation_strategy": ["趋势交易", "加速接力", "平台突破"],
        "buy_point_type": ["B15 底背离买点", "支撑买点", "平台突破确认买点"],
        "signal_status": ["未处理", "已确认买入", "已忽略", "已失效"],
        "signal_user_action": ["未处理", "已确认买入", "已忽略", "标记误报"],
        "trade_status": ["持仓中", "部分卖出", "已完成", "已取消", "已失效"],
        "review_status": ["待填写", "填写中", "已完成", "已归档"],
        "issue_tag": ["追高买入", "止损犹豫", "止盈不及时", "仓位过重", "情绪化交易", "非信号交易"],
        "attribution_type": [
            "市场问题",
            "板块问题",
            "个股问题",
            "买点问题",
            "卖点问题",
            "仓位问题",
            "纪律问题",
            "情绪问题",
            "策略问题",
            "数据问题",
        ],
    }
    TASKS = [
        ("collect_market_daily", "market"),
        ("collect_hot_sector_rank", "market"),
        ("collect_hot_stock_rank", "market"),
        ("collect_limit_up_daily", "market"),
        ("update_watch_daily_kline", "kline"),
        ("update_watch_15m_kline", "kline"),
        ("scan_watch_signals", "signal"),
        ("scan_trade_risk_signals", "signal"),
        ("generate_weekly_review_form", "review"),
        ("generate_monthly_review_form", "review"),
        ("remind_pending_review_form", "review"),
        ("aggregate_review_metrics", "review"),
    ]
    TEMPLATES = ["买入观察信号", "卖出提醒", "风险提醒", "复盘提醒", "任务异常提醒"]

    def __init__(self, db: Session):
        self.db = db

    def init_defaults(self) -> dict:
        created = 0
        for dict_type, values in self.DICTS.items():
            for order, label in enumerate(values, start=1):
                if not self.db.query(ConfigDictionary).filter_by(dict_type=dict_type, dict_value=label).first():
                    self.db.add(
                        ConfigDictionary(
                            dict_type=dict_type,
                            dict_label=label,
                            dict_value=label,
                            sort_order=order,
                        )
                    )
                    created += 1
        for name, owner in self.TASKS:
            if not self.db.query(ConfigTask).filter_by(task_name=name).first():
                self.db.add(ConfigTask(task_name=name, task_type="scheduled", owner_module=owner, enabled=True))
                created += 1
        for name in self.DICTS["buy_point_type"]:
            if not self.db.query(ConfigStrategy).filter_by(strategy_name=name).first():
                self.db.add(
                    ConfigStrategy(
                        strategy_name=name,
                        strategy_type="buy",
                        buy_point_type=name,
                        enabled=True,
                    )
                )
                created += 1
        for name in self.TEMPLATES:
            if not self.db.query(ConfigNotificationTemplate).filter_by(push_type=name, channel="site").first():
                self.db.add(
                    ConfigNotificationTemplate(
                        push_type=name,
                        channel="site",
                        title_template=name,
                        content_template=f"{name}: {{content}}\n{ASSISTANT_NOTE}",
                    )
                )
                created += 1
            if not self.db.query(MyNotificationSetting).filter_by(push_type=name, channel="site").first():
                self.db.add(MyNotificationSetting(push_type=name, channel="site", enabled=True))
                created += 1
        for review_type in ["weekly", "monthly", "trade"]:
            if not self.db.query(ConfigReviewTemplate).filter_by(review_type=review_type).first():
                self.db.add(ConfigReviewTemplate(review_type=review_type, template_name=f"{review_type} 默认模板"))
                created += 1
        if not self.db.query(MyUserProfile).first():
            self.db.add(MyUserProfile(nickname="Aquant User", bio="单用户交易复盘训练系统"))
            created += 1
        self.db.commit()
        return {"created": created}


class PrdMarketDataService:
    def __init__(self, db: Session):
        self.db = db

    def _daily_chances(self, trade_date: date) -> list[dict]:
        rows = (
            self.db.query(MktDailyChance)
            .filter(MktDailyChance.trade_date == trade_date)
            .order_by(MktDailyChance.rank_no.asc(), MktDailyChance.id.asc())
            .all()
        )
        result = []
        for row in rows:
            stocks = (
                self.db.query(MktDailyChanceStock)
                .filter(MktDailyChanceStock.chance_id == row.id)
                .order_by(MktDailyChanceStock.id.asc())
                .all()
            )
            result.append({
                "source": row.platform,
                "kind": "today_chance",
                "subject_id": row.subject_id,
                "subject_name": row.subject_name,
                "title": row.article_title,
                "article_id": row.article_id,
                "article_time": row.article_time,
                "attention_num": row.attention_num,
                "stocks": [
                    {
                        "stock_code": stock.stock_code,
                        "stock_name": stock.stock_name,
                        "change_pct": stock.change_pct,
                        "last_price": stock.last_price,
                    }
                    for stock in stocks
                ],
            })
        return result

    def _daily_tuyeres(self, trade_date: date) -> list[dict]:
        rows = (
            self.db.query(MktDailyTuyere)
            .filter(MktDailyTuyere.trade_date == trade_date)
            .order_by(MktDailyTuyere.rank_no.asc(), MktDailyTuyere.id.asc())
            .all()
        )
        result = []
        for row in rows:
            stocks = (
                self.db.query(MktDailyTuyereStock)
                .filter(MktDailyTuyereStock.tuyere_id == row.id)
                .order_by(MktDailyTuyereStock.id.asc())
                .all()
            )
            result.append({
                "source": row.platform,
                "kind": "today_tuyere",
                "subject_id": row.subject_id,
                "subject_name": row.subject_name,
                "title": row.driver,
                "driver": row.driver,
                "attention_num": row.attention_num,
                "stocks": [
                    {
                        "stock_code": stock.stock_code,
                        "stock_name": stock.stock_name,
                        "change_pct": stock.change_pct,
                        "last_price": stock.last_price,
                    }
                    for stock in stocks
                ],
            })
        return result

    def _daily_topics(self, trade_date: date) -> list[dict]:
        rows = (
            self.db.query(MktDailyTopic)
            .filter(MktDailyTopic.trade_date == trade_date)
            .order_by(MktDailyTopic.rank_no.asc(), MktDailyTopic.id.asc())
            .all()
        )
        result = []
        for row in rows:
            stocks = (
                self.db.query(MktDailyTopicStock)
                .filter(MktDailyTopicStock.topic_id == row.id)
                .order_by(MktDailyTopicStock.id.asc())
                .all()
            )
            result.append({
                "source": row.platform,
                "rank_no": row.rank_no,
                "topic_code": row.topic_code,
                "title": row.title,
                "description": row.description,
                "subtitle": row.subtitle,
                "hot_value": row.hot_value,
                "jump_url": row.jump_url,
                "stocks": [
                    {
                        "stock_code": stock.stock_code,
                        "stock_name": stock.stock_name,
                        "change_pct": stock.change_pct,
                    }
                    for stock in stocks
                ],
            })
        return result

    def _limit_up_ladder(self, trade_date: date) -> list[dict]:
        rows = (
            self.db.query(MktLimitUpLadder)
            .filter(MktLimitUpLadder.trade_date == trade_date)
            .order_by(MktLimitUpLadder.height.desc())
            .all()
        )
        result = []
        for row in rows:
            stocks = (
                self.db.query(MktLimitUpLadderStock)
                .filter(MktLimitUpLadderStock.ladder_id == row.id)
                .order_by(MktLimitUpLadderStock.id.asc())
                .all()
            )
            result.append({
                "height": row.height,
                "count": row.stock_count,
                "stocks": [
                    {"stock_code": stock.stock_code, "stock_name": stock.stock_name}
                    for stock in stocks
                ],
            })
        return result

    def get_market_overview(self, trade_date: date) -> dict:
        row = (
            self.db.query(MktDaily)
            .filter(MktDaily.trade_date == trade_date, MktDaily.source == "real")
            .order_by(MktDaily.collected_at.desc())
            .first()
        ) or (
            self.db.query(MktDaily)
            .filter(MktDaily.trade_date == trade_date)
            .order_by(MktDaily.collected_at.desc())
            .first()
        )
        if not row:
            return {"trade_date": trade_date.isoformat(), "items": [], "note": "当前日期暂无市场数据"}

        # Compute index change from previous trading day
        prev_row = (
            self.db.query(MktDaily)
            .filter(MktDaily.trade_date < trade_date)
            .order_by(MktDaily.trade_date.desc())
            .first()
        )
        def calc_index_change(current: float | None, previous: float | None) -> float | None:
            if current is None or previous is None or previous == 0:
                return None
            return round((current - previous) / previous * 100, 2)

        sh_index_change_pct = (
            row.sh_index_change_pct
            if row.sh_index_change_pct is not None
            else calc_index_change(row.sh_index, prev_row.sh_index if prev_row else None)
        )
        sz_index_change_pct = (
            row.sz_index_change_pct
            if row.sz_index_change_pct is not None
            else calc_index_change(row.sz_index, prev_row.sz_index if prev_row else None)
        )
        cyb_index_change_pct = (
            row.cyb_index_change_pct
            if row.cyb_index_change_pct is not None
            else calc_index_change(row.cyb_index, prev_row.cyb_index if prev_row else None)
        )

        total = (row.up_count or 0) + (row.down_count or 0) + (row.flat_count or 0)
        up_ratio = row.up_count / total if total else 0
        # Generate commentary
        parts = []
        if row.sh_index and row.sh_index > 0:
            change_str = f"{sh_index_change_pct:+.2f}%" if sh_index_change_pct is not None else ""
            parts.append(f"上证指数 {row.sh_index:.0f} 点{(' ' + change_str) if change_str else ''}")
            parts.append("市场普涨，情绪积极")
        elif up_ratio >= 0.5:
            parts.append("市场分化，涨跌互现")
        elif up_ratio >= 0.3:
            parts.append("市场偏弱，多数个股下跌")
        else:
            parts.append("市场弱势，注意风险控制")
        if row.total_amount:
            amt = row.total_amount / 10000
            if amt > 2:
                parts.append(f"成交额 {amt:.2f} 万亿，交投活跃")
            elif amt > 1:
                parts.append(f"成交额 {amt:.2f} 万亿，交投正常")
            else:
                parts.append(f"成交额 {amt:.2f} 万亿，交投低迷")
        if row.limit_up_count:
            parts.append(f"涨停 {row.limit_up_count} 家")
            if row.max_continue_board and row.max_continue_board >= 4:
                parts.append(f"最高连板 {row.max_continue_board} 板，短线情绪较高")
        if row.limit_down_count and row.limit_down_count > 10:
            parts.append(f"跌停 {row.limit_down_count} 家，注意风险释放")

        market_comment = "；".join(parts) + "。仅作为交易辅助，请结合个人交易规则确认。"

        return {
            "trade_date": row.trade_date.isoformat(),
            "source": row.source,
            "sh_index": row.sh_index,
            "sz_index": row.sz_index,
            "cyb_index": row.cyb_index,
            "index_change_pct": sh_index_change_pct,
            "sh_index_change_pct": sh_index_change_pct,
            "sh_index_change_px": row.sh_index_change_px,
            "sz_index_change_pct": sz_index_change_pct,
            "sz_index_change_px": row.sz_index_change_px,
            "cyb_index_change_pct": cyb_index_change_pct,
            "cyb_index_change_px": row.cyb_index_change_px,
            "index_trade_status": row.index_trade_status or {},
            "today_chances": self._daily_chances(row.trade_date),
            "today_tuyeres": self._daily_tuyeres(row.trade_date),
            "topic_list": self._daily_topics(row.trade_date),
            "limit_up_ladder": self._limit_up_ladder(row.trade_date),
            "total_amount": row.total_amount,
            "up_count": row.up_count,
            "down_count": row.down_count,
            "flat_count": row.flat_count,
            "limit_up_count": row.limit_up_count,
            "limit_down_count": row.limit_down_count,
            "broken_limit_count": row.broken_limit_count,
            "max_continue_board": row.max_continue_board,
            "source_url": row.source_url,
            "source_update_time": row.source_update_time,
            "collected_at": row.collected_at,
            "market_comment": market_comment,
        }

    def get_hot_boards(self, trade_date: date | None = None, platform: str | None = None) -> list[dict]:
        query = self.db.query(MktHotBoard)
        if trade_date:
            query = query.filter(MktHotBoard.trade_date == trade_date)
        if platform:
            query = query.filter(MktHotBoard.platform == platform)
        return [self._board_dict(row) for row in query.order_by(MktHotBoard.platform, MktHotBoard.platform_rank).all()]

    PRIMES = [29, 23, 19, 17, 13, 11, 7, 5, 3, 2]  # rank 1..10 → descending primes

    def get_hot_stocks(self, trade_date: date | None = None, platform: str | None = None) -> list[dict]:
        # If platform filter requested, return raw platform data
        if platform:
            query = self.db.query(MktHotStock)
            if trade_date:
                query = query.filter(MktHotStock.trade_date == trade_date)
            query = query.filter(MktHotStock.platform == platform)
            return [self._hot_stock_dict(row) for row in query.order_by(MktHotStock.platform_rank).limit(10).all()]

        # Cross-platform prime-score ranking
        all_rows = self.db.query(MktHotStock).filter(MktHotStock.trade_date == trade_date).all() if trade_date else []
        platform_stocks: dict[str, list] = {}
        for row in all_rows:
            platform_stocks.setdefault(row.platform, []).append(row)

        scores: dict[str, dict] = {}  # stock_code → {total_score, stock_name, platforms}
        for _, rows in platform_stocks.items():
            rows.sort(key=lambda r: r.platform_rank or 99)
            for idx, row in enumerate(rows[:10]):
                score = self.PRIMES[idx] if idx < len(self.PRIMES) else 1
                entry = scores.setdefault(row.stock_code, {"total_score": 0, "stock_name": row.stock_name, "platforms": [], "best_rank": 99, "price": None, "change_pct": None})
                entry["total_score"] += score
                entry["best_rank"] = min(entry["best_rank"], idx + 1)
                entry["platforms"].append({"platform": row.platform, "rank": idx + 1, "score": score})
                if row.price and not entry["price"]:
                    entry["price"] = row.price
                if row.change_pct is not None and entry["change_pct"] is None:
                    entry["change_pct"] = row.change_pct

        ranked = sorted(scores.items(), key=lambda x: x[1]["total_score"], reverse=True)[:10]
        return [
            {
                "stock_code": code,
                "stock_name": info["stock_name"],
                "total_score": info["total_score"],
                "best_rank": info["best_rank"],
                "platforms": info["platforms"],
                "cross_platform": len(info["platforms"]) >= 2,
                "price": info["price"],
                "change_pct": info["change_pct"],
            }
            for code, info in ranked
        ]

    def get_limit_ups(self, trade_date: date | None = None, platform: str | None = None) -> list[dict]:
        stock_query = self.db.query(MktLimitUpStock)
        if trade_date:
            stock_query = stock_query.filter(MktLimitUpStock.trade_date == trade_date)
        if platform:
            stock_query = stock_query.filter(MktLimitUpStock.platform == platform)
        stock_rows = stock_query.order_by(MktLimitUpStock.limit_time, MktLimitUpStock.stock_code).all()
        if stock_rows:
            return [self._limit_up_stock_dict(row) for row in stock_rows]

        query = self.db.query(MktLimitUp)
        if trade_date:
            query = query.filter(MktLimitUp.trade_date == trade_date)
        if platform:
            query = query.filter(MktLimitUp.platform == platform)
        return [self._limit_up_dict(row) for row in query.order_by(MktLimitUp.limit_time, MktLimitUp.stock_code).all()]

    def get_stock_source_summary(self, stock_code: str, trade_date: date) -> dict:
        code = normalize_stock_code(stock_code)
        hot = self.db.query(MktHotStock).filter_by(stock_code=code, trade_date=trade_date).all()
        limit_stock_rows = self.db.query(MktLimitUpStock).filter_by(stock_code=code, trade_date=trade_date).all()
        limit_rows = self.db.query(MktLimitUp).filter_by(stock_code=code, trade_date=trade_date).all()
        return {
            "stock_code": code,
            "hot_sources": [self._hot_stock_dict(item) for item in hot],
            "limit_sources": [self._limit_up_stock_dict(item) for item in limit_stock_rows] or [self._limit_up_dict(item) for item in limit_rows],
            "xueqiu_url": xueqiu_link(code),
        }

    def get_latest_source(self, stock_code: str) -> dict:
        code = normalize_stock_code(stock_code)
        hot = self.db.query(MktHotStock).filter_by(stock_code=code).order_by(MktHotStock.trade_date.desc()).first()
        limit_stock_row = self.db.query(MktLimitUpStock).filter_by(stock_code=code).order_by(MktLimitUpStock.trade_date.desc()).first()
        limit_row = self.db.query(MktLimitUp).filter_by(stock_code=code).order_by(MktLimitUp.trade_date.desc()).first()
        return {
            "stock_code": code,
            "latest_hot": self._hot_stock_dict(hot) if hot else None,
            "latest_limit": self._limit_up_stock_dict(limit_stock_row) if limit_stock_row else (self._limit_up_dict(limit_row) if limit_row else None),
            "xueqiu_url": xueqiu_link(code),
        }

    @staticmethod
    def _board_dict(row: MktHotBoard) -> dict:
        return {
            key: getattr(row, key)
            for key in [
                "id",
                "trade_date",
                "platform",
                "board_name",
                "platform_rank",
                "raw_score",
                "change_pct",
                "leader_stock_code",
                "leader_stock_name",
                "reason",
                "source_url",
                "source_update_time",
                "collected_at",
            ]
        }

    @staticmethod
    def _hot_stock_dict(row: MktHotStock) -> dict:
        return {
            key: getattr(row, key)
            for key in [
                "id",
                "trade_date",
                "platform",
                "stock_code",
                "stock_name",
                "board_name",
                "platform_rank",
                "raw_score",
                "raw_reason",
                "price",
                "change_pct",
                "source_url",
                "source_update_time",
                "collected_at",
            ]
        }

    @staticmethod
    def _limit_up_dict(row: MktLimitUp) -> dict:
        return {
            key: getattr(row, key)
            for key in [
                "id",
                "trade_date",
                "platform",
                "stock_code",
                "stock_name",
                "limit_time",
                "last_limit_time",
                "open_limit_count",
                "seal_amount",
                "seal_volume",
                "turnover_rate",
                "amount",
                "board_count",
                "concept",
                "limit_reason",
                "limit_type",
                "source_url",
                "source_update_time",
                "collected_at",
            ]
        }

    @staticmethod
    def _limit_up_stock_dict(row: MktLimitUpStock) -> dict:
        return {
            "id": row.id,
            "trade_date": row.trade_date,
            "platform": row.platform,
            "stock_code": row.stock_code,
            "stock_name": row.stock_name,
            "limit_time": str(row.limit_time or "").split(" ")[-1][:5] or row.limit_time,
            "last_limit_time": row.limit_time,
            "open_limit_count": None,
            "seal_amount": None,
            "seal_volume": None,
            "turnover_rate": None,
            "amount": None,
            "board_count": row.board_count or row.ladder_height or 1,
            "concept": row.plate_name,
            "limit_reason": row.limit_reason,
            "limit_type": row.reason_tags,
            "source_url": None,
            "source_update_time": row.source_update_time,
            "collected_at": row.collected_at,
            "change_pct": row.change_pct,
            "last_price": row.last_price,
            "ladder_height": row.ladder_height,
            "plate_code": row.plate_code,
            "plate_name": row.plate_name,
        }


class PrdWatchPoolService:
    ACTIVE_STATUSES = ["watching", "triggered", "holding", "not_trade"]

    def __init__(self, db: Session):
        self.db = db

    def list_watch_pool(self, pool_status: str | None = None) -> list[WatchPool]:
        query = self.db.query(WatchPool)
        if pool_status:
            query = query.filter(WatchPool.pool_status == pool_status)
        else:
            query = query.filter(WatchPool.active.is_(True))
        return query.order_by(WatchPool.created_at.desc()).all()

    def add_watch(self, payload: dict) -> WatchPool:
        code = normalize_stock_code(payload["stock_code"])
        existing = (
            self.db.query(WatchPool)
            .filter(WatchPool.stock_code == code, WatchPool.pool_status.in_(self.ACTIVE_STATUSES))
            .first()
        )
        if existing:
            return self.update_watch(existing.id, payload)
        entity = WatchPool(
            stock_code=code,
            stock_name=payload.get("stock_name") or code,
            sector_name=payload.get("sector_name") or payload.get("board_name"),
            reason=payload.get("reason") or payload.get("source_reason") or "用户手动加入自选",
            labels=payload.get("labels") or [],
            pool_status="watching",
            monitor_enabled=True,
            operation_strategies=payload.get("operation_strategies") or [],
            buy_point_types=payload.get("buy_point_types") or [],
            source_type=payload.get("source_type") or "manual",
            source_platform=payload.get("source_platform"),
            source_rank=payload.get("source_rank"),
            source_score=payload.get("source_score"),
            source_reason=payload.get("source_reason") or "",
            xueqiu_url=xueqiu_link(code),
            entry_price=payload.get("entry_price"),
            remark=payload.get("remark") or "",
            added_trade_date=date.today(),
        )
        self.db.add(entity)
        self.db.flush()
        self._log(entity, None, "watching", "用户手动加入自选")
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update_watch(self, watch_id: int, payload: dict) -> WatchPool:
        entity = self.get_watch(watch_id)
        for key in ["labels", "operation_strategies", "buy_point_types", "remark", "reason", "entry_price", "pool_status", "monitor_enabled", "sector_name"]:
            if key in payload:
                setattr(entity, key, payload[key])
        self.db.commit()
        return entity

    def get_watch(self, watch_id: int) -> WatchPool:
        entity = self.db.query(WatchPool).filter(WatchPool.id == watch_id).first()
        if not entity:
            raise ValueError("watch not found")
        return entity

    def remove_watch(self, watch_id: int, reason: str) -> WatchPool:
        entity = self.get_watch(watch_id)
        old = entity.pool_status
        entity.pool_status = "removed"
        entity.active = False
        entity.archive_reason = reason
        self._log(entity, old, "removed", reason)
        self.db.commit()
        return entity

    def restore_watch(self, watch_id: int) -> WatchPool:
        entity = self.get_watch(watch_id)
        old = entity.pool_status
        entity.pool_status = "watching"
        entity.active = True
        entity.monitor_enabled = True
        self._log(entity, old, "watching", "用户恢复观察")
        self.db.commit()
        return entity

    def blacklist_watch(self, watch_id: int, reason: str) -> WatchPool:
        entity = self.get_watch(watch_id)
        old = entity.pool_status
        entity.pool_status = "blacklist"
        entity.is_blacklist = True
        entity.blacklist_reason = reason
        entity.active = False
        self._log(entity, old, "blacklist", reason)
        self.db.commit()
        return entity

    def unblacklist_watch(self, watch_id: int, reason: str) -> WatchPool:
        entity = self.get_watch(watch_id)
        old = entity.pool_status
        entity.pool_status = "watching"
        entity.is_blacklist = False
        entity.active = True
        self._log(entity, old, "watching", reason)
        self.db.commit()
        return entity

    def set_monitor(self, watch_id: int, enabled: bool, reason: str = "") -> WatchPool:
        entity = self.get_watch(watch_id)
        entity.monitor_enabled = enabled
        self.db.commit()
        return entity

    def summary(self) -> dict:
        statuses = ["watching", "triggered", "holding", "not_trade", "completed", "removed", "blacklist"]
        return {status: self.db.query(WatchPool).filter(WatchPool.pool_status == status).count() for status in statuses}

    def logs(self, watch_id: int) -> list[WatchPoolStatusLog]:
        return (
            self.db.query(WatchPoolStatusLog)
            .filter(WatchPoolStatusLog.watch_id == watch_id)
            .order_by(WatchPoolStatusLog.operated_at.desc())
            .all()
        )

    def _log(self, entity: WatchPool, from_status: str | None, to_status: str, reason: str) -> None:
        self.db.add(
            WatchPoolStatusLog(
                watch_id=entity.id,
                stock_code=entity.stock_code,
                from_status=from_status,
                to_status=to_status,
                change_reason=reason,
                operator_type="user",
            )
        )


def record_operation(
    db: Session,
    operation_type: str,
    target_type: str,
    target_id: str = "",
    summary: str = "",
    payload: dict | None = None,
) -> None:
    db.add(
        ConfigOperationLog(
            operation_type=operation_type,
            target_type=target_type,
            target_id=str(target_id),
            summary=summary,
            payload=payload or {},
        )
    )
