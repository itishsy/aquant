from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CandleBase, SystemBase


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class StockBasic(TimestampMixin, SystemBase):
    __tablename__ = "stock_basic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    exchange: Mapped[str] = mapped_column(String(8))
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_st: Mapped[bool] = mapped_column(Boolean, default=False)
    is_delisting_risk: Mapped[bool] = mapped_column(Boolean, default=False)


class MarketDaily(TimestampMixin, SystemBase):
    __tablename__ = "market_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True, unique=True)
    sh_index: Mapped[float] = mapped_column(Float)
    sz_index: Mapped[float] = mapped_column(Float)
    cyb_index: Mapped[float] = mapped_column(Float)
    total_amount: Mapped[float] = mapped_column(Float)
    up_count: Mapped[int] = mapped_column(Integer)
    down_count: Mapped[int] = mapped_column(Integer)
    flat_count: Mapped[int] = mapped_column(Integer, default=0)
    up_ratio: Mapped[float] = mapped_column(Float)
    limit_up_count: Mapped[int] = mapped_column(Integer)
    limit_down_count: Mapped[int] = mapped_column(Integer)
    broken_limit_count: Mapped[int] = mapped_column(Integer)
    broken_limit_ratio: Mapped[float] = mapped_column(Float)
    max_continue_board: Mapped[int] = mapped_column(Integer)
    yesterday_limit_avg_return: Mapped[float] = mapped_column(Float, default=0.0)
    north_money: Mapped[float] = mapped_column(Float, default=0.0)
    market_score: Mapped[float] = mapped_column(Float, default=0.0)
    market_status: Mapped[str] = mapped_column(String(16), default="震荡")
    market_comment: Mapped[str] = mapped_column(Text, default="")


class MarketReviewDaily(TimestampMixin, SystemBase):
    __tablename__ = "market_review_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True, unique=True)
    review_text: Mapped[str] = mapped_column(Text, default="")
    concept: Mapped[str] = mapped_column(Text, default="")
    chance: Mapped[list] = mapped_column(JSON, default=list)
    tuyere: Mapped[list] = mapped_column(JSON, default=list)
    topic: Mapped[list] = mapped_column(JSON, default=list)
    subject: Mapped[list] = mapped_column(JSON, default=list)
    fund: Mapped[dict] = mapped_column(JSON, default=dict)
    latent: Mapped[list] = mapped_column(JSON, default=list)
    raw_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)


class SectorDaily(TimestampMixin, SystemBase):
    __tablename__ = "sector_daily"
    __table_args__ = (
        Index("ix_sector_daily_sector_name_trade_date", "sector_name", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    sector_name: Mapped[str] = mapped_column(String(64), index=True)
    change_pct: Mapped[float] = mapped_column(Float)
    limit_up_count: Mapped[int] = mapped_column(Integer)
    leader_stock_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    leader_stock_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    leader_board_count: Mapped[int] = mapped_column(Integer, default=0)
    fund_strength: Mapped[float] = mapped_column(Float, default=0.0)
    continuity_days: Mapped[int] = mapped_column(Integer, default=0)
    heat_spread: Mapped[float] = mapped_column(Float, default=0.0)
    sector_score: Mapped[float] = mapped_column(Float, default=0.0)
    sector_type: Mapped[str] = mapped_column(String(16), default="轮动板块")
    reason: Mapped[str] = mapped_column(Text, default="")
    risk_hint: Mapped[str] = mapped_column(Text, default="")


class HotStockRank(TimestampMixin, SystemBase):
    __tablename__ = "hot_stock_rank"
    __table_args__ = (
        Index("ix_hot_stock_rank_stock_code_trade_date", "stock_code", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[str] = mapped_column(String(32))
    platform_rank: Mapped[int] = mapped_column(Integer)
    rank_score: Mapped[int] = mapped_column(Integer)
    resonance_score: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    is_limit_up: Mapped[bool] = mapped_column(Boolean, default=False)
    is_continue_board: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class LimitUpDaily(TimestampMixin, SystemBase):
    __tablename__ = "limit_up_daily"
    __table_args__ = (
        Index("ix_limit_up_daily_stock_code_trade_date", "stock_code", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    limit_time: Mapped[str] = mapped_column(String(16))
    open_limit_count: Mapped[int] = mapped_column(Integer, default=0)
    seal_amount: Mapped[float] = mapped_column(Float, default=0.0)
    seal_volume: Mapped[float] = mapped_column(Float, default=0.0)
    turnover_rate: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    board_count: Mapped[int] = mapped_column(Integer, default=1)
    concept: Mapped[str] = mapped_column(String(128), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    is_first_board: Mapped[bool] = mapped_column(Boolean, default=True)
    is_continue_board: Mapped[bool] = mapped_column(Boolean, default=False)
    limit_type: Mapped[str] = mapped_column(String(32), default="首板涨停")
    risk_flag: Mapped[str] = mapped_column(String(64), default="")


class WatchPool(TimestampMixin, SystemBase):
    __tablename__ = "watch_pool"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    labels: Mapped[list] = mapped_column(JSON, default=list)
    strategy_type: Mapped[str] = mapped_column(String(64), default="manual")
    is_blacklist: Mapped[bool] = mapped_column(Boolean, default=False)
    blacklist_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_price: Mapped[float] = mapped_column(Float, default=0.0)
    latest_change_pct: Mapped[float] = mapped_column(Float, default=0.0)
    last_signal_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_trade_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default="watching", index=True)
    pool_layer: Mapped[str] = mapped_column(String(32), default="L2_watch", index=True)
    entry_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sector_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observe_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_observe_days: Mapped[int] = mapped_column(Integer, default=30)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    archive_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pool_status: Mapped[str] = mapped_column(String(32), default="观察中", index=True)
    monitor_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    operation_strategies: Mapped[list] = mapped_column(JSON, default=list)
    buy_point_types: Mapped[list] = mapped_column(JSON, default=list)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_reason: Mapped[str] = mapped_column(Text, default="")
    xueqiu_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    removed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class StockKlineDaily(TimestampMixin, CandleBase):
    __tablename__ = "stock_kline_daily"
    __table_args__ = (
        Index("ix_stock_kline_daily_stock_code_trade_date", "stock_code", "trade_date", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    prev_close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)
    change_pct: Mapped[float] = mapped_column(Float)


class StockKline15m(TimestampMixin, CandleBase):
    __tablename__ = "stock_kline_15m"
    __table_args__ = (
        Index("ix_stock_kline_15m_stock_code_trade_time", "stock_code", "trade_time", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    trade_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    prev_close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)
    change_pct: Mapped[float] = mapped_column(Float)


class SignalRecord(TimestampMixin, SystemBase):
    __tablename__ = "signal_record"
    __table_args__ = (
        Index("ix_signal_record_signal_type", "signal_type"),
        Index("ix_signal_record_strategy_name", "strategy_name"),
        Index("ix_signal_record_stock_code_trigger_time", "stock_code", "trigger_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signal_type: Mapped[str] = mapped_column(String(16))
    signal_text: Mapped[str] = mapped_column(String(32))
    strategy_name: Mapped[str] = mapped_column(String(64))
    signal_level: Mapped[str] = mapped_column(String(8), default="B")
    trigger_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    current_price: Mapped[float] = mapped_column(Float)
    trigger_reason: Mapped[str] = mapped_column(Text)
    risk_desc: Mapped[str] = mapped_column(Text, default="")
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    invalid_condition: Mapped[str] = mapped_column(Text, default="")
    market_status: Mapped[str] = mapped_column(String(16), default="震荡")
    valid: Mapped[bool] = mapped_column(Boolean, default=True)
    handled_status: Mapped[str] = mapped_column(String(16), default="new")
    raw_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    plan_item_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    checklist_required: Mapped[bool] = mapped_column(Boolean, default=True)
    signal_invalidated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    invalid_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class StrategyConfig(TimestampMixin, SystemBase):
    __tablename__ = "strategy_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    strategy_type: Mapped[str] = mapped_column(String(16))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)


class TradeRecord(TimestampMixin, SystemBase):
    __tablename__ = "trade_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int] = mapped_column(Integer, index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    buy_price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    position_ratio: Mapped[float] = mapped_column(Float)
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    trade_plan: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="open")
    sell_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sell_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    plan_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    plan_item_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    is_unplanned: Mapped[bool] = mapped_column(Boolean, default=False)
    discipline_flags: Mapped[dict] = mapped_column(JSON, default=dict)
    review_status: Mapped[str] = mapped_column(String(32), default="pending")
    trade_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class TradeReview(TimestampMixin, SystemBase):
    __tablename__ = "trade_review"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_id: Mapped[int] = mapped_column(Integer, index=True, unique=True)
    review_type: Mapped[str] = mapped_column(String(16), default="single")
    week_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    week_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    failure_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_notes: Mapped[str] = mapped_column(Text, default="")
    system_summary: Mapped[str] = mapped_column(Text, default="")


class DailyPlan(TimestampMixin, SystemBase):
    __tablename__ = "daily_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(128))
    focus: Mapped[str] = mapped_column(Text, default="")
    risk_rule: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")


class SystemTaskLog(TimestampMixin, SystemBase):
    __tablename__ = "system_task_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_rows: Mapped[int] = mapped_column(Integer, default=0)


class WatchPoolLifecycle(SystemBase):
    __tablename__ = "watch_pool_lifecycle"
    __table_args__ = (
        Index("ix_watch_pool_lifecycle_stock_created", "stock_code", "created_at"),
    )

    lifecycle_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), index=True)
    action_type: Mapped[str] = mapped_column(String(32))
    action_reason: Mapped[str] = mapped_column(Text, default="")
    operator_type: Mapped[str] = mapped_column(String(16), default="system")
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WatchPoolScore(SystemBase):
    __tablename__ = "watch_pool_score"
    __table_args__ = (
        Index("ix_watch_pool_score_stock_trade_date", "stock_code", "trade_date"),
    )

    score_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    market_score: Mapped[float] = mapped_column(Float, default=0.0)
    sector_score: Mapped[float] = mapped_column(Float, default=0.0)
    hot_score: Mapped[float] = mapped_column(Float, default=0.0)
    technical_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    liquidity_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    entry_level: Mapped[str] = mapped_column(String(32), index=True)
    score_detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DailyTradePlan(TimestampMixin, SystemBase):
    __tablename__ = "daily_trade_plan"

    plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    market_score: Mapped[float] = mapped_column(Float, default=0.0)
    market_state: Mapped[str] = mapped_column(String(32), default="震荡")
    trade_permission: Mapped[str] = mapped_column(String(32), default="cautious")
    max_total_position: Mapped[float] = mapped_column(Float, default=0.5)
    max_single_position: Mapped[float] = mapped_column(Float, default=0.2)
    key_sectors: Mapped[list] = mapped_column(JSON, default=list)
    risk_summary: Mapped[str] = mapped_column(Text, default="")
    discipline_note: Mapped[str] = mapped_column(
        Text, default="仅作为交易辅助，请结合个人交易计划确认。"
    )
    plan_status: Mapped[str] = mapped_column(String(32), default="draft")
    execution_summary: Mapped[dict] = mapped_column(JSON, default=dict)


class DailyTradePlanItem(TimestampMixin, SystemBase):
    __tablename__ = "daily_trade_plan_item"

    item_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    action_type: Mapped[str] = mapped_column(String(32), default="buy_watch")
    trigger_condition: Mapped[str] = mapped_column(Text, default="")
    expected_price_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_price_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_ratio: Mapped[float] = mapped_column(Float, default=0.1)
    invalid_condition: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    source_type: Mapped[str] = mapped_column(String(32), default="watch_pool")
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_reward_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_note: Mapped[str] = mapped_column(Text, default="")


class TradeExecutionChecklist(SystemBase):
    __tablename__ = "trade_execution_checklist"

    checklist_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    plan_item_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    trade_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    market_check: Mapped[bool] = mapped_column(Boolean, default=True)
    sector_check: Mapped[bool] = mapped_column(Boolean, default=True)
    position_check: Mapped[bool] = mapped_column(Boolean, default=True)
    signal_check: Mapped[bool] = mapped_column(Boolean, default=True)
    stop_loss_check: Mapped[bool] = mapped_column(Boolean, default=True)
    target_check: Mapped[bool] = mapped_column(Boolean, default=True)
    position_size_check: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_reward_check: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_trade_count_check: Mapped[bool] = mapped_column(Boolean, default=True)
    emotion_check: Mapped[bool] = mapped_column(Boolean, default=True)
    all_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_items: Mapped[list] = mapped_column(JSON, default=list)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SellPlan(TimestampMixin, SystemBase):
    __tablename__ = "sell_plan"

    sell_plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_id: Mapped[int] = mapped_column(Integer, index=True)
    sell_signal_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    sell_type: Mapped[str] = mapped_column(String(32), default="manual")
    planned_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sell_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_reason: Mapped[str] = mapped_column(Text, default="")
    system_suggested: Mapped[bool] = mapped_column(Boolean, default=True)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    pnl_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_comment: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="pending")


class TradeErrorTag(SystemBase):
    __tablename__ = "trade_error_tag"

    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_name: Mapped[str] = mapped_column(String(64), unique=True)
    tag_type: Mapped[str] = mapped_column(String(32), default="discipline")
    description: Mapped[str] = mapped_column(Text, default="")
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TradeReviewDetail(TimestampMixin, SystemBase):
    __tablename__ = "trade_review_detail"

    detail_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    buy_signal_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    buy_plan_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    market_state_at_buy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sector_state_at_buy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entry_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    exit_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    max_profit_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    max_loss_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    final_pnl_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    holding_days: Mapped[int] = mapped_column(Integer, default=0)
    risk_reward_actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    stop_loss_executed: Mapped[bool] = mapped_column(Boolean, default=False)
    target_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    target_executed: Mapped[bool] = mapped_column(Boolean, default=False)
    plan_execution_result: Mapped[str] = mapped_column(String(64), default="")
    user_answers: Mapped[dict] = mapped_column(JSON, default=dict)
    error_tags: Mapped[list] = mapped_column(JSON, default=list)
    improvement_action: Mapped[str] = mapped_column(Text, default="")
    trade_score: Mapped[float] = mapped_column(Float, default=0.0)


class WeeklyReview(TimestampMixin, SystemBase):
    __tablename__ = "weekly_review"
    __table_args__ = (Index("ix_weekly_review_range", "week_start", "week_end"),)

    weekly_review_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    week_end: Mapped[date] = mapped_column(Date, index=True)
    market_summary: Mapped[str] = mapped_column(Text, default="")
    sector_summary: Mapped[str] = mapped_column(Text, default="")
    watch_pool_summary: Mapped[str] = mapped_column(Text, default="")
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    profit_loss_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    expectancy: Mapped[float] = mapped_column(Float, default=0.0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    avg_holding_days: Mapped[float] = mapped_column(Float, default=0.0)
    plan_execution_rate: Mapped[float] = mapped_column(Float, default=0.0)
    unplanned_trade_count: Mapped[int] = mapped_column(Integer, default=0)
    stop_loss_execution_rate: Mapped[float] = mapped_column(Float, default=0.0)
    take_profit_execution_rate: Mapped[float] = mapped_column(Float, default=0.0)
    signal_trade_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    emotion_trade_count: Mapped[int] = mapped_column(Integer, default=0)
    best_trade_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    worst_trade_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    next_week_focus: Mapped[str] = mapped_column(Text, default="")
    next_week_discipline: Mapped[str] = mapped_column(
        Text, default="仅作为交易辅助，请结合个人交易计划确认。"
    )
    user_summary: Mapped[str] = mapped_column(Text, default="")


class MonthlyReview(TimestampMixin, SystemBase):
    __tablename__ = "monthly_review"

    monthly_review_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[str] = mapped_column(String(7), unique=True, index=True)
    monthly_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_return: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    profit_loss_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    expectancy: Mapped[float] = mapped_column(Float, default=0.0)
    best_strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    worst_strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    best_sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    worst_sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plan_execution_rate: Mapped[float] = mapped_column(Float, default=0.0)
    discipline_score: Mapped[float] = mapped_column(Float, default=0.0)
    review_completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    ability_score: Mapped[dict] = mapped_column(JSON, default=dict)
    top_errors: Mapped[list] = mapped_column(JSON, default=list)
    next_month_goals: Mapped[dict] = mapped_column(JSON, default=dict)


class DisciplineRule(TimestampMixin, SystemBase):
    __tablename__ = "discipline_rule"

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    rule_type: Mapped[str] = mapped_column(String(32), default="risk")
    rule_value: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    strict_mode_required: Mapped[bool] = mapped_column(Boolean, default=False)


class UserTradingScore(SystemBase):
    __tablename__ = "user_trading_score"

    score_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_type: Mapped[str] = mapped_column(String(16), index=True)
    period_key: Mapped[str] = mapped_column(String(16), index=True)
    stock_selection_score: Mapped[float] = mapped_column(Float, default=0.0)
    entry_score: Mapped[float] = mapped_column(Float, default=0.0)
    exit_score: Mapped[float] = mapped_column(Float, default=0.0)
    position_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_control_score: Mapped[float] = mapped_column(Float, default=0.0)
    execution_score: Mapped[float] = mapped_column(Float, default=0.0)
    review_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    score_detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NotificationRecord(SystemBase):
    __tablename__ = "notification_record"

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notification_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(128), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MktDaily(TimestampMixin, SystemBase):
    __tablename__ = "mkt_daily"
    __table_args__ = (UniqueConstraint("trade_date", "source", name="uq_mkt_daily_trade_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(32), default="mock", index=True)
    sh_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    sz_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    cyb_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    down_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flat_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_down_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    broken_limit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_continue_board: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    raw_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)


class MktHotBoard(TimestampMixin, SystemBase):
    __tablename__ = "mkt_hot_board"
    __table_args__ = (
        UniqueConstraint("trade_date", "platform", "board_name", name="uq_mkt_hot_board_day_platform_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    board_name: Mapped[str] = mapped_column(String(128), index=True)
    platform_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    leader_stock_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    leader_stock_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class MktHotStock(TimestampMixin, SystemBase):
    __tablename__ = "mkt_hot_stock"
    __table_args__ = (
        UniqueConstraint("trade_date", "platform", "stock_code", name="uq_mkt_hot_stock_day_platform_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    board_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    platform_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_reason: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class MktLimitUp(TimestampMixin, SystemBase):
    __tablename__ = "mkt_limit_up"
    __table_args__ = (
        UniqueConstraint("trade_date", "platform", "stock_code", name="uq_mkt_limit_up_day_platform_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    limit_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_limit_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    open_limit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seal_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    seal_volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    board_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    concept: Mapped[str] = mapped_column(String(128), default="")
    limit_reason: Mapped[str] = mapped_column(Text, default="")
    limit_type: Mapped[str] = mapped_column(String(64), default="")
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class MktStockKlineDaily(TimestampMixin, CandleBase):
    __tablename__ = "mkt_stock_kline_daily"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", "source", name="uq_mkt_daily_kline_code_day_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(32), default="mock", index=True)
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma5: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma10: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_dif: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_dea: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_hist: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MktStockKline15m(TimestampMixin, CandleBase):
    __tablename__ = "mkt_stock_kline_15m"
    __table_args__ = (
        UniqueConstraint("stock_code", "kline_time", "source", name="uq_mkt_15m_kline_code_time_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    kline_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str] = mapped_column(String(32), default="mock", index=True)
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma5: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma10: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_dif: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_dea: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_hist: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class WatchSignal(TimestampMixin, SystemBase):
    __tablename__ = "watch_signal"
    __table_args__ = (
        UniqueConstraint(
            "stock_code",
            "buy_point_type",
            "signal_type",
            "trigger_date",
            name="uq_watch_signal_code_point_type_date",
        ),
    )

    signal_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watch_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    signal_type: Mapped[str] = mapped_column(String(32), index=True)
    buy_point_type: Mapped[str] = mapped_column(String(64), default="")
    strategy_name: Mapped[str] = mapped_column(String(64), index=True)
    signal_level: Mapped[str] = mapped_column(String(8), default="B")
    kline_period: Mapped[str] = mapped_column(String(16), default="")
    trigger_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    trigger_date: Mapped[date] = mapped_column(Date, index=True)
    trigger_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    trigger_reason: Mapped[str] = mapped_column(Text, default="")
    risk_desc: Mapped[str] = mapped_column(Text, default="")
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    invalid_condition: Mapped[str] = mapped_column(Text, default="")
    signal_status: Mapped[str] = mapped_column(String(32), default="未处理", index=True)
    user_action: Mapped[str] = mapped_column(String(32), default="未处理")
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    related_trade_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)


class WatchSignalPerformance(TimestampMixin, SystemBase):
    __tablename__ = "watch_signal_performance"
    __table_args__ = (UniqueConstraint("signal_id", name="uq_watch_signal_performance_signal_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int] = mapped_column(Integer, index=True)
    watch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    trigger_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    follow_return_1d: Mapped[float | None] = mapped_column(Float, nullable=True)
    follow_return_3d: Mapped[float | None] = mapped_column(Float, nullable=True)
    follow_return_5d: Mapped[float | None] = mapped_column(Float, nullable=True)
    follow_return_10d: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_return_after_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown_after_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_confirmed_trade: Mapped[bool] = mapped_column(Boolean, default=False)
    related_trade_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class WatchPoolStatusLog(SystemBase):
    __tablename__ = "watch_pool_status_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watch_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), index=True)
    change_reason: Mapped[str] = mapped_column(Text, default="")
    operator_type: Mapped[str] = mapped_column(String(16), default="user")
    operated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WatchTrade(TimestampMixin, SystemBase):
    __tablename__ = "watch_trade"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    watch_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    trade_source: Mapped[str] = mapped_column(String(32), default="信号确认")
    buy_point_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_buy_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_buy_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_buy_amount: Mapped[float] = mapped_column(Float, default=0.0)
    average_buy_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_sell_amount: Mapped[float] = mapped_column(Float, default=0.0)
    remaining_amount: Mapped[float] = mapped_column(Float, default=0.0)
    position_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_amount: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    max_profit_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_loss_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    holding_days: Mapped[int] = mapped_column(Integer, default=0)
    trade_status: Mapped[str] = mapped_column(String(32), default="持仓中", index=True)
    result_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")


class WatchTradeExecution(SystemBase):
    __tablename__ = "watch_trade_execution"
    __table_args__ = (Index("ix_watch_trade_execution_trade_time", "trade_id", "execution_time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_id: Mapped[int] = mapped_column(Integer, index=True)
    signal_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    watch_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    execution_type: Mapped[str] = mapped_column(String(32), index=True)
    execution_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    execution_price: Mapped[float] = mapped_column(Float)
    execution_amount: Mapped[float] = mapped_column(Float)
    execution_reason: Mapped[str] = mapped_column(Text, default="")
    pnl_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    holding_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_full_exit: Mapped[bool] = mapped_column(Boolean, default=False)
    result_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReviewForm(TimestampMixin, SystemBase):
    __tablename__ = "review_form"
    __table_args__ = (UniqueConstraint("review_type", "review_period", name="uq_review_form_type_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_type: Mapped[str] = mapped_column(String(16), index=True)
    review_period: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="待填写", index=True)
    title: Mapped[str] = mapped_column(String(128), default="")
    system_summary: Mapped[str] = mapped_column(Text, default="")
    user_summary: Mapped[str] = mapped_column(Text, default="")
    improvement_plan: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class ReviewWeekly(TimestampMixin, SystemBase):
    __tablename__ = "review_weekly"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(Integer, index=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    week_end: Mapped[date] = mapped_column(Date, index=True)
    market_summary: Mapped[str] = mapped_column(Text, default="")
    hot_board_changes: Mapped[str] = mapped_column(Text, default="")
    watch_pool_changes: Mapped[str] = mapped_column(Text, default="")
    trade_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    signal_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    error_stats: Mapped[dict] = mapped_column(JSON, default=dict)
    next_week_plan: Mapped[str] = mapped_column(Text, default="")


class ReviewMonthly(TimestampMixin, SystemBase):
    __tablename__ = "review_monthly"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    market_summary: Mapped[str] = mapped_column(Text, default="")
    sector_summary: Mapped[str] = mapped_column(Text, default="")
    trade_result: Mapped[dict] = mapped_column(JSON, default=dict)
    strategy_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    top_errors: Mapped[list] = mapped_column(JSON, default=list)
    next_month_plan: Mapped[str] = mapped_column(Text, default="")


class ReviewTrade(TimestampMixin, SystemBase):
    __tablename__ = "review_trade"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    trade_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    signal_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    market_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    entry_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_profit_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_loss_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_pnl_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    issue_tags: Mapped[list] = mapped_column(JSON, default=list)
    attribution_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_comment: Mapped[str] = mapped_column(Text, default="")
    improvement_action: Mapped[str] = mapped_column(Text, default="")
    trade_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="待填写", index=True)


class MyUserProfile(TimestampMixin, SystemBase):
    __tablename__ = "my_user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str] = mapped_column(String(64), default="Aquant 用户")
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bio: Mapped[str] = mapped_column(Text, default="")


class MyUserPreference(TimestampMixin, SystemBase):
    __tablename__ = "my_user_preference"
    __table_args__ = (
        UniqueConstraint("preference_type", "preference_key", name="uq_my_preference_type_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    preference_type: Mapped[str] = mapped_column(String(64), index=True)
    preference_key: Mapped[str] = mapped_column(String(64), index=True)
    preference_value: Mapped[dict] = mapped_column(JSON, default=dict)


class MyNotificationSetting(TimestampMixin, SystemBase):
    __tablename__ = "my_notification_setting"
    __table_args__ = (UniqueConstraint("push_type", "channel", name="uq_my_notification_type_channel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    push_type: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="site")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_time: Mapped[dict] = mapped_column(JSON, default=dict)


class ConfigDataSource(TimestampMixin, SystemBase):
    __tablename__ = "config_data_source"

    source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(64), index=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    platform: Mapped[str] = mapped_column(String(32), default="")
    auth_type: Mapped[str] = mapped_column(String(32), default="none")
    base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigTask(TimestampMixin, SystemBase):
    __tablename__ = "config_task"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    task_type: Mapped[str] = mapped_column(String(32), index=True)
    owner_module: Mapped[str] = mapped_column(String(32), default="")
    cron_expression: Mapped[str] = mapped_column(String(128), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    retry_times: Mapped[int] = mapped_column(Integer, default=0)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=300)
    running: Mapped[bool] = mapped_column(Boolean, default=False)


class ConfigTaskLog(SystemBase):
    __tablename__ = "config_task_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    task_name: Mapped[str] = mapped_column(String(64), index=True)
    run_status: Mapped[str] = mapped_column(String(16), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_rows: Mapped[int] = mapped_column(Integer, default=0)


class ConfigFieldMapping(TimestampMixin, SystemBase):
    __tablename__ = "config_field_mapping"

    mapping_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    platform: Mapped[str] = mapped_column(String(32), default="")
    data_type: Mapped[str] = mapped_column(String(32), index=True)
    raw_field_name: Mapped[str] = mapped_column(String(128))
    standard_field_name: Mapped[str] = mapped_column(String(128))
    field_type: Mapped[str] = mapped_column(String(32), default="string")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    transform_rule: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigDictionary(TimestampMixin, SystemBase):
    __tablename__ = "config_dictionary"
    __table_args__ = (UniqueConstraint("dict_type", "dict_value", name="uq_config_dictionary_type_value"),)

    dict_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dict_type: Mapped[str] = mapped_column(String(64), index=True)
    dict_label: Mapped[str] = mapped_column(String(128))
    dict_value: Mapped[str] = mapped_column(String(128))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, default="")


class ConfigStrategy(TimestampMixin, SystemBase):
    __tablename__ = "config_strategy"

    strategy_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    strategy_type: Mapped[str] = mapped_column(String(32), index=True)
    buy_point_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    scan_period: Mapped[str] = mapped_column(String(32), default="")
    dedup_rule: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigNotificationTemplate(TimestampMixin, SystemBase):
    __tablename__ = "config_notification_template"

    template_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    push_type: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="site")
    title_template: Mapped[str] = mapped_column(String(128), default="")
    content_template: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigNotificationRecord(SystemBase):
    __tablename__ = "config_notification_record"
    __table_args__ = (
        UniqueConstraint(
            "push_type",
            "target_type",
            "target_id",
            "channel",
            name="uq_config_notification_record_target",
        ),
    )

    record_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    push_type: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str] = mapped_column(String(64), default="")
    target_id: Mapped[str] = mapped_column(String(64), default="")
    channel: Mapped[str] = mapped_column(String(32), default="site")
    title: Mapped[str] = mapped_column(String(128), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    send_status: Mapped[str] = mapped_column(String(32), default="unread", index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ConfigReviewTemplate(TimestampMixin, SystemBase):
    __tablename__ = "config_review_template"

    template_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_type: Mapped[str] = mapped_column(String(32), index=True)
    template_name: Mapped[str] = mapped_column(String(128))
    fields_json: Mapped[list] = mapped_column(JSON, default=list)
    version: Mapped[str] = mapped_column(String(16), default="1.0")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigOperationLog(SystemBase):
    __tablename__ = "config_operation_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator_id: Mapped[str] = mapped_column(String(64), default="single-user", index=True)
    operation_type: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str] = mapped_column(String(64), index=True)
    target_id: Mapped[str] = mapped_column(String(64), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
