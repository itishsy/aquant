from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ApiMessage(BaseModel):
    message: str = "ok"


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str = "Aquant"


class SignalOut(BaseModel):
    id: int
    stock_code: str
    stock_name: str
    sector_name: str | None = None
    signal_type: str
    signal_text: str
    strategy_name: str
    signal_level: str
    trigger_time: datetime
    current_price: float
    trigger_reason: str
    risk_desc: str
    invalid_condition: str
    market_status: str
    raw_snapshot: dict[str, Any]

    class Config:
        from_attributes = True


class WatchPoolCreate(BaseModel):
    stock_code: str
    reason: str
    labels: list[str] = Field(default_factory=list)
    strategy_type: str = "manual"


class WatchPoolUpdateLabels(BaseModel):
    labels: list[str]


class BlacklistPayload(BaseModel):
    reason: str


class TradeConfirmPayload(BaseModel):
    price: float = Field(gt=0)
    quantity: int = Field(gt=0)
    position: float = Field(gt=0, le=1)
    stop_loss_price: float | None = Field(default=None, gt=0)
    target_price: float | None = Field(default=None, gt=0)
    trade_plan: str = ""


class TradeSellPayload(BaseModel):
    price: float = Field(gt=0)
    quantity: int = Field(gt=0)
    reason: str


class TradeOut(BaseModel):
    id: int
    signal_id: int
    stock_code: str
    stock_name: str
    buy_price: float
    quantity: int
    position_ratio: float
    stop_loss_price: float | None = None
    target_price: float | None = None
    trade_plan: str
    status: str
    sell_price: float | None = None
    sell_quantity: int | None = None
    sell_reason: str | None = None
    realized_pnl: float | None = None
    sell_time: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewPayload(BaseModel):
    user_notes: str = ""
    failure_reason: str | None = None


class WeeklyReviewOut(BaseModel):
    week_start: date
    week_end: date
    metrics: dict[str, Any]
    system_summary: str
    user_notes: str = ""


class DailyPlanCreate(BaseModel):
    plan_date: date
    title: str = Field(min_length=1, max_length=128)
    focus: str = ""
    risk_rule: str = ""
    note: str = ""


class DailyPlanOut(BaseModel):
    id: int
    plan_date: date
    title: str
    focus: str
    risk_rule: str
    note: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WeeklyReviewNotePayload(BaseModel):
    week_start: date
    week_end: date
    user_notes: str = ""
