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


class MktStockQuote(TimestampMixin, SystemBase):
    __tablename__ = "mkt_stock_quote"
    __table_args__ = (UniqueConstraint("stock_code", name="uq_mkt_stock_quote_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    latest_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="real")
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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
    sh_index_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sh_index_change_px: Mapped[float | None] = mapped_column(Float, nullable=True)
    sz_index_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sz_index_change_px: Mapped[float | None] = mapped_column(Float, nullable=True)
    cyb_index_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    cyb_index_change_px: Mapped[float | None] = mapped_column(Float, nullable=True)
    index_trade_status: Mapped[dict] = mapped_column(JSON, default=dict)
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


class MktDailyPlate(TimestampMixin, SystemBase):
    __tablename__ = "mkt_daily_plate"
    __table_args__ = (
        UniqueConstraint("trade_date", "plate_type", "platform", "plate_code", name="uq_mkt_daily_plate_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    plate_type: Mapped[str] = mapped_column(String(32), default="limit_up", index=True)
    platform: Mapped[str] = mapped_column(String(32), default="cls", index=True)
    rank_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plate_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    plate_name: Mapped[str] = mapped_column(String(128), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    jump_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    def __init__(self, **kwargs):
        if "source" in kwargs and "plate_type" not in kwargs:
            kwargs["plate_type"] = kwargs.pop("source")
        kwargs.pop("plate_key", None)
        if "reason" in kwargs and "description" not in kwargs:
            kwargs["description"] = kwargs.pop("reason")
        if "up_reason" in kwargs:
            if kwargs["up_reason"]:
                kwargs["description"] = kwargs["up_reason"]
            kwargs.pop("up_reason", None)
        if "title" in kwargs and "plate_name" not in kwargs:
            kwargs["plate_name"] = kwargs.pop("title")
        for legacy_key in (
            "subject_id",
            "article_id",
            "article_time",
            "attention_num",
            "article_title",
            "change_pct",
            "raw_score",
            "limit_up_count",
            "source_update_time",
            "collected_at",
        ):
            kwargs.pop(legacy_key, None)
        super().__init__(**kwargs)


class MktDailyPlateStock(TimestampMixin, SystemBase):
    __tablename__ = "mkt_daily_plate_stock"
    __table_args__ = (UniqueConstraint("plate_id", "stock_code", name="uq_mkt_daily_plate_stock"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plate_id: Mapped[int] = mapped_column(Integer, index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_price: Mapped[float | None] = mapped_column(Float, nullable=True)


class MktDailyTopic(TimestampMixin, SystemBase):
    __tablename__ = "mkt_daily_topic"
    __table_args__ = (UniqueConstraint("trade_date", "source", "topic_code", name="uq_mkt_daily_topic_day_source_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(32), default="real", index=True)
    platform: Mapped[str] = mapped_column(String(32), default="ths", index=True)
    rank_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    topic_code: Mapped[str] = mapped_column(String(64), default="", index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    subtitle: Mapped[str] = mapped_column(Text, default="")
    hot_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    jump_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MktDailyTopicStock(TimestampMixin, SystemBase):
    __tablename__ = "mkt_daily_topic_stock"
    __table_args__ = (UniqueConstraint("topic_id", "stock_code", name="uq_mkt_daily_topic_stock"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(Integer, index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)


class MktLimitUpPlate(TimestampMixin, SystemBase):
    __tablename__ = "mkt_limit_up_plate"
    __table_args__ = (UniqueConstraint("trade_date", "source", "plate_code", name="uq_mkt_limit_plate_day_source_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(32), default="real", index=True)
    platform: Mapped[str] = mapped_column(String(32), default="cls", index=True)
    plate_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    plate_name: Mapped[str] = mapped_column(String(128), default="", index=True)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    limit_up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    up_reason: Mapped[str] = mapped_column(Text, default="")
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MktLimitUpStock(TimestampMixin, SystemBase):
    __tablename__ = "mkt_limit_up_stock"
    __table_args__ = (UniqueConstraint("trade_date", "source", "stock_code", name="uq_mkt_limit_stock_day_source_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    source: Mapped[str] = mapped_column(String(32), default="real", index=True)
    platform: Mapped[str] = mapped_column(String(32), default="cls", index=True)
    raw_secu_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    plate_code: Mapped[str] = mapped_column(String(32), default="", index=True)
    plate_name: Mapped[str] = mapped_column(String(128), default="", index=True)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    circulating_market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    limit_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    limit_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    board_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    board_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    board_text: Mapped[str] = mapped_column(String(64), default="")
    limit_reason: Mapped[str] = mapped_column(Text, default="")
    reason_tags: Mapped[str] = mapped_column(String(256), default="")
    ladder_height: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class MktHotStock(SystemBase):
    __tablename__ = "mkt_hot_stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64))
    assoc_plate: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cls_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ths_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tgb_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tag: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


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


class MktStockKline(TimestampMixin, SystemBase):
    __tablename__ = "mkt_stock_kline"
    __table_args__ = (
        UniqueConstraint("stock_code", "timeframe", "kline_time", "source", name="uq_mkt_stock_kline_code_tf_time_source"),
        Index("ix_mkt_stock_kline_code_tf_time", "stock_code", "timeframe", "kline_time"),
        Index("ix_mkt_stock_kline_code_tf_date", "stock_code", "timeframe", "trade_date"),
    )

    kline_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), index=True)
    kline_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(32), default="mock", index=True)
    source_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AutoStrategyRun(SystemBase):
    __tablename__ = "auto_strategy_run"
    __table_args__ = (
        Index("ix_auto_strategy_run_code_type_started", "strategy_code", "run_type", "started_at"),
        Index("ix_auto_strategy_run_status_started", "status", "started_at"),
    )

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_code: Mapped[str] = mapped_column(String(64), index=True)
    run_type: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running", index=True)
    message: Mapped[str] = mapped_column(Text, default="")
    stats_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AutoCandidate(TimestampMixin, SystemBase):
    __tablename__ = "auto_candidate"
    __table_args__ = (
        Index("ix_auto_candidate_strategy_stock", "strategy_code", "stock_code"),
        Index("ix_auto_candidate_strategy_status", "strategy_code", "status"),
        Index("ix_auto_candidate_strategy_selected_date", "strategy_code", "selected_trade_date"),
        Index("ix_auto_candidate_strategy_hot_rank_date", "strategy_code", "hot_rank_date"),
    )

    candidate_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_code: Mapped[str] = mapped_column(String(64), index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="watching", index=True)
    selected_trade_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    hot_rank_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    hot_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hot_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    filter_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    latest_signal_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    position_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AutoSignal(SystemBase):
    __tablename__ = "auto_signal"
    __table_args__ = (
        Index("ix_auto_signal_candidate_type_time", "candidate_id", "signal_type", "timeframe", "trigger_time"),
        Index("ix_auto_signal_strategy_stock", "strategy_code", "stock_code"),
        Index("ix_auto_signal_position", "position_id"),
        Index("ix_auto_signal_status_created", "signal_status", "created_at"),
    )

    signal_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    position_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    strategy_code: Mapped[str] = mapped_column(String(64), index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    signal_type: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), index=True)
    trigger_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    trigger_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_status: Mapped[str] = mapped_column(String(32), default="generated", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AutoPaperPosition(TimestampMixin, SystemBase):
    __tablename__ = "auto_paper_position"
    __table_args__ = (
        Index("ix_auto_position_strategy_stock_status", "strategy_code", "stock_code", "status"),
        Index("ix_auto_position_candidate", "candidate_id"),
        Index("ix_auto_position_status_created", "status", "created_at"),
    )

    position_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(Integer, index=True)
    strategy_code: Mapped[str] = mapped_column(String(64), index=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    entry_signal_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    entry_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_amount_cash: Mapped[float] = mapped_column(Float, default=10000.0)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_signal_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_reason: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    pnl_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)


class WatchPool(TimestampMixin, SystemBase):
    __tablename__ = "watch_pool"
    __table_args__ = (
        Index("ix_watch_pool_code_status", "stock_code", "status"),
        Index("ix_watch_pool_trading_system", "trading_system"),
        Index("ix_watch_pool_trading_system_code", "trading_system_code"),
        Index("ix_watch_pool_system_stage", "system_stage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    sector_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    labels: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="watching", index=True)
    monitor_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    operation_strategies: Mapped[list] = mapped_column(JSON, default=list)
    buy_point_types: Mapped[list] = mapped_column(JSON, default=list)
    entry_source: Mapped[str] = mapped_column(String(32), default="manual", index=True)
    entry_reason: Mapped[str] = mapped_column(Text, default="")
    trading_system: Mapped[str | None] = mapped_column(String(32), nullable=True)
    trading_system_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    system_stage: Mapped[str] = mapped_column(String(32), default="observe")
    system_params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    active_rule_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_recommendation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    key_observe_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    auto_remove_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    invalid_condition: Mapped[str] = mapped_column(Text, default="")
    risk_tags: Mapped[list] = mapped_column(JSON, default=list)
    signal_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    latest_signal_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_remark: Mapped[str] = mapped_column(Text, default="")
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    remark: Mapped[str] = mapped_column(Text, default="")
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
    operation_type: Mapped[str] = mapped_column(String(32), default="status_change")
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    operator_type: Mapped[str] = mapped_column(String(16), default="user")
    operated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WatchSignal(TimestampMixin, SystemBase):
    __tablename__ = "watch_signal"
    __table_args__ = (
        UniqueConstraint("stock_code", "buy_point_type", "signal_type", "trigger_date", name="uq_watch_signal_code_point_type_date"),
        Index("ix_watch_signal_watch_status", "watch_id", "signal_status"),
        Index("ix_watch_signal_trigger_signature", "trigger_signature"),
    )

    signal_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watch_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    signal_type: Mapped[str] = mapped_column(String(32), index=True)
    buy_point_type: Mapped[str] = mapped_column(String(64), default="")
    trading_system: Mapped[str | None] = mapped_column(String(32), nullable=True)
    trading_system_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rule_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    rule_type: Mapped[str] = mapped_column(String(32), default="")
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
    buy_point_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    buy_point_confirm_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    buy_point_confirm_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    abandoned_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    abandoned_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    abandoned_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    prevent_duplicate_signal: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    signal_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    user_action: Mapped[str] = mapped_column(String(32), default="pending")
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    related_trade_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notification_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notification_error: Mapped[str | None] = mapped_column(Text, nullable=True)


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
    __table_args__ = (Index("ix_watch_trade_watch_status", "watch_id", "trade_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    signal_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    watch_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    stock_code: Mapped[str] = mapped_column(String(16), index=True)
    stock_name: Mapped[str] = mapped_column(String(64), default="")
    trade_source: Mapped[str] = mapped_column(String(32), default="signal")
    buy_point_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trading_system: Mapped[str | None] = mapped_column(String(32), nullable=True)
    trading_system_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_rule_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    system_params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    active_sell_rule_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    active_stop_rule_codes_json: Mapped[list] = mapped_column(JSON, default=list)
    current_stage: Mapped[str] = mapped_column(String(32), default="trading")
    latest_trade_signal_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
    buy_reason: Mapped[str] = mapped_column(Text, default="")
    trade_plan: Mapped[str] = mapped_column(Text, default="")
    emotion_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
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
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
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


class TradingSystemDefinition(TimestampMixin, SystemBase):
    __tablename__ = "trading_system_definition"
    __table_args__ = (UniqueConstraint("system_code", name="uq_trading_system_definition_code"),)

    system_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    system_name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    lifecycle_desc: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)


class TradingRuleDefinition(TimestampMixin, SystemBase):
    __tablename__ = "trading_rule_definition"
    __table_args__ = (UniqueConstraint("rule_code", name="uq_trading_rule_definition_code"),)

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(128), index=True)
    rule_type: Mapped[str] = mapped_column(String(32), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), index=True)
    executor_key: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class TradingSystemParamDefinition(TimestampMixin, SystemBase):
    __tablename__ = "trading_system_param_definition"
    __table_args__ = (
        UniqueConstraint("system_code", "param_key", name="uq_trading_system_param_definition_system_key"),
        Index("ix_trading_system_param_system_order", "system_code", "sort_order"),
    )

    param_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_code: Mapped[str] = mapped_column(String(64), index=True)
    param_key: Mapped[str] = mapped_column(String(64), index=True)
    param_name: Mapped[str] = mapped_column(String(128))
    param_type: Mapped[str] = mapped_column(String(32), index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class TradingSystemRuleBinding(TimestampMixin, SystemBase):
    __tablename__ = "trading_system_rule_binding"
    __table_args__ = (
        UniqueConstraint("system_code", "rule_code", "stage", name="uq_trading_system_rule_binding_identity"),
        Index("ix_trading_system_rule_binding_system_stage_order", "system_code", "stage", "sort_order"),
    )

    binding_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_code: Mapped[str] = mapped_column(String(64), index=True)
    rule_code: Mapped[str] = mapped_column(String(64), index=True)
    stage: Mapped[str] = mapped_column(String(32), index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    logic_group: Mapped[str] = mapped_column(String(64), default="", index=True)
    logic_operator: Mapped[str] = mapped_column(String(8), default="AND")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)


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


class PlanDaily(TimestampMixin, SystemBase):
    __tablename__ = "plan_daily"
    __table_args__ = (UniqueConstraint("plan_date", name="uq_plan_daily_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    today_position: Mapped[str] = mapped_column(String(32), default="")
    operation_summary: Mapped[str] = mapped_column(Text, default="")
    execution_status: Mapped[str] = mapped_column(String(32), default="")
    tomorrow_plan: Mapped[str] = mapped_column(Text, default="")


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
