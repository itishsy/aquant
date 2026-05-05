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
    MktHotBoard,
    MktHotStock,
    MktLimitUp,
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

    def get_market_overview(self, trade_date: date) -> dict:
        row = (
            self.db.query(MktDaily)
            .filter(MktDaily.trade_date == trade_date)
            .order_by(MktDaily.collected_at.desc())
            .first()
        )
        if not row:
            return {"trade_date": trade_date.isoformat(), "items": [], "note": "当前日期暂无市场数据"}
        return {
            "trade_date": row.trade_date.isoformat(),
            "source": row.source,
            "sh_index": row.sh_index,
            "sz_index": row.sz_index,
            "cyb_index": row.cyb_index,
            "index_change_pct": row.index_change_pct,
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
        }

    def get_hot_boards(self, trade_date: date | None = None, platform: str | None = None) -> list[dict]:
        query = self.db.query(MktHotBoard)
        if trade_date:
            query = query.filter(MktHotBoard.trade_date == trade_date)
        if platform:
            query = query.filter(MktHotBoard.platform == platform)
        return [self._board_dict(row) for row in query.order_by(MktHotBoard.platform, MktHotBoard.platform_rank).all()]

    def get_hot_stocks(self, trade_date: date | None = None, platform: str | None = None) -> list[dict]:
        query = self.db.query(MktHotStock)
        if trade_date:
            query = query.filter(MktHotStock.trade_date == trade_date)
        if platform:
            query = query.filter(MktHotStock.platform == platform)
        return [self._hot_stock_dict(row) for row in query.order_by(MktHotStock.platform, MktHotStock.platform_rank).all()]

    def get_limit_ups(self, trade_date: date | None = None, platform: str | None = None) -> list[dict]:
        query = self.db.query(MktLimitUp)
        if trade_date:
            query = query.filter(MktLimitUp.trade_date == trade_date)
        if platform:
            query = query.filter(MktLimitUp.platform == platform)
        return [self._limit_up_dict(row) for row in query.order_by(MktLimitUp.platform, MktLimitUp.stock_code).all()]

    def get_stock_source_summary(self, stock_code: str, trade_date: date) -> dict:
        code = normalize_stock_code(stock_code)
        hot = self.db.query(MktHotStock).filter_by(stock_code=code, trade_date=trade_date).all()
        limit_rows = self.db.query(MktLimitUp).filter_by(stock_code=code, trade_date=trade_date).all()
        return {
            "stock_code": code,
            "hot_sources": [self._hot_stock_dict(item) for item in hot],
            "limit_sources": [self._limit_up_dict(item) for item in limit_rows],
            "xueqiu_url": xueqiu_link(code),
        }

    def get_latest_source(self, stock_code: str) -> dict:
        code = normalize_stock_code(stock_code)
        hot = self.db.query(MktHotStock).filter_by(stock_code=code).order_by(MktHotStock.trade_date.desc()).first()
        limit_row = self.db.query(MktLimitUp).filter_by(stock_code=code).order_by(MktLimitUp.trade_date.desc()).first()
        return {
            "stock_code": code,
            "latest_hot": self._hot_stock_dict(hot) if hot else None,
            "latest_limit": self._limit_up_dict(limit_row) if limit_row else None,
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
        for key in ["labels", "operation_strategies", "buy_point_types", "remark", "reason", "entry_price"]:
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
