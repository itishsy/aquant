from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import SystemBase


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StockBasic(TimestampMixin, SystemBase):
    __tablename__ = "stock_basic"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    stock_name: Mapped[str] = mapped_column(String(64), index=True)
    exchange: Mapped[str] = mapped_column(String(8), default="")
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_st: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MktDaily(TimestampMixin, SystemBase):
    __tablename__ = "mkt_daily"
    __table_args__ = (UniqueConstraint("trade_date", "source", name="uq_mkt_daily_trade_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(32), default="mock", index=True)
    sh_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    sz_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    cyb_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    index_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
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
    __table_args__ = (UniqueConstraint("trade_date", "platform", "board_name", name="uq_mkt_hot_board_day_platform_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    board_name: Mapped[str] = mapped_column(String(128), index=True)
    platform_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    leader_stock_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    leader_stock_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    leading_stocks: Mapped[list] = mapped_column(JSON, default=list)
    reason: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class MktHotStock(TimestampMixin, SystemBase):
    __tablename__ = "mkt_hot_stock"
    __table_args__ = (UniqueConstraint("trade_date", "platform", "stock_code", name="uq_mkt_hot_stock_day_platform_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    board_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    platform_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_reason: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)


class MktLimitUp(TimestampMixin, SystemBase):
    __tablename__ = "mkt_limit_up"
    __table_args__ = (UniqueConstraint("trade_date", "platform", "stock_code", name="uq_mkt_limit_up_day_platform_code"),)

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


class MktStockKlineDaily(TimestampMixin, SystemBase):
    __tablename__ = "mkt_stock_kline_daily"
    __table_args__ = (UniqueConstraint("stock_code", "trade_date", "source", name="uq_mkt_daily_kline_code_day_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(32), default="mock", index=True)
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    ma5: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma10: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_dif: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_dea: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_hist: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MktStockKline15m(TimestampMixin, SystemBase):
    __tablename__ = "mkt_stock_kline_15m"
    __table_args__ = (UniqueConstraint("stock_code", "kline_time", "source", name="uq_mkt_15m_kline_code_time_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    kline_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str] = mapped_column(String(32), default="mock", index=True)
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    macd_dif: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_dea: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_hist: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class WatchPool(TimestampMixin, SystemBase):
    __tablename__ = "watch_pool"
    __table_args__ = (Index("ix_watch_pool_code_status", "stock_code", "pool_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    labels: Mapped[list] = mapped_column(JSON, default=list)
    pool_status: Mapped[str] = mapped_column(String(32), default="watching", index=True)
    monitor_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    operation_strategies: Mapped[list] = mapped_column(JSON, default=list)
    buy_point_types: Mapped[list] = mapped_column(JSON, default=list)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_reason: Mapped[str] = mapped_column(Text, default="")
    xueqiu_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")
    is_blacklist: Mapped[bool] = mapped_column(Boolean, default=False)
    blacklist_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_trade_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    archive_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


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


class WatchSignal(TimestampMixin, SystemBase):
    __tablename__ = "watch_signal"
    __table_args__ = (UniqueConstraint("stock_code", "buy_point_type", "signal_type", "trigger_date", name="uq_watch_signal_code_point_type_date"),)

    signal_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watch_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
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
    signal_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    user_action: Mapped[str] = mapped_column(String(32), default="pending")
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


class WatchTrade(TimestampMixin, SystemBase):
    __tablename__ = "watch_trade"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    watch_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    trade_source: Mapped[str] = mapped_column(String(32), default="signal")
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
    trade_status: Mapped[str] = mapped_column(String(32), default="open", index=True)
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
    stock_name: Mapped[str] = mapped_column(String(64), default="")
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
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
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
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)


class MyUserProfile(TimestampMixin, SystemBase):
    __tablename__ = "my_user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str] = mapped_column(String(64), default="Aquant User")
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bio: Mapped[str] = mapped_column(Text, default="")


class MyUserPreference(TimestampMixin, SystemBase):
    __tablename__ = "my_user_preference"
    __table_args__ = (UniqueConstraint("preference_type", "preference_key", name="uq_my_preference_type_key"),)

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
    transform_rule: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigDictionary(TimestampMixin, SystemBase):
    __tablename__ = "config_dictionary"
    __table_args__ = (UniqueConstraint("dict_type", "dict_value", name="uq_config_dictionary_type_value"),)

    dict_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dict_type: Mapped[str] = mapped_column(String(64), index=True)
    dict_label: Mapped[str] = mapped_column(String(128))
    dict_value: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigStrategy(TimestampMixin, SystemBase):
    __tablename__ = "config_strategy"

    strategy_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    strategy_type: Mapped[str] = mapped_column(String(32), index=True)
    buy_point_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigNotificationTemplate(TimestampMixin, SystemBase):
    __tablename__ = "config_notification_template"
    __table_args__ = (UniqueConstraint("push_type", "channel", name="uq_config_notification_template_type_channel"),)

    template_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    push_type: Mapped[str] = mapped_column(String(64), index=True)
    channel: Mapped[str] = mapped_column(String(32), default="site")
    title_template: Mapped[str] = mapped_column(String(128), default="")
    content_template: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigNotificationRecord(SystemBase):
    __tablename__ = "config_notification_record"
    __table_args__ = (UniqueConstraint("push_type", "target_type", "target_id", "channel", name="uq_config_notification_record_target"),)

    record_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    push_type: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str] = mapped_column(String(64), default="")
    target_id: Mapped[str] = mapped_column(String(64), default="")
    channel: Mapped[str] = mapped_column(String(32), default="site")
    title: Mapped[str] = mapped_column(String(128), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    send_status: Mapped[str] = mapped_column(String(32), default="unread", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ConfigReviewTemplate(TimestampMixin, SystemBase):
    __tablename__ = "config_review_template"

    template_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_type: Mapped[str] = mapped_column(String(16), index=True)
    template_name: Mapped[str] = mapped_column(String(128))
    fields_json: Mapped[list] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ConfigOperationLog(SystemBase):
    __tablename__ = "config_operation_log"

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str] = mapped_column(String(64), index=True)
    target_id: Mapped[str] = mapped_column(String(64), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    operator: Mapped[str] = mapped_column(String(64), default="single-admin")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
