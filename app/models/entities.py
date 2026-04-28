from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Index, Integer, String, Text
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
