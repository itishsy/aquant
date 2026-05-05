from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import ConfigTaskLog, MktStockKline15m, MktStockKlineDaily


class DataQualityError(ValueError):
    """Raised when incoming data violates validation rules."""


class DataQualityService:
    @staticmethod
    def validate_required(payload: dict, required_fields: list[str]) -> None:
        for field in required_fields:
            if payload.get(field) in (None, ""):
                raise DataQualityError(f"{field} is required")

    @staticmethod
    def validate_ohlc(payload: dict) -> None:
        o = payload["open"]
        h = payload["high"]
        l = payload["low"]
        c = payload["close"]
        if not (l <= o <= h and l <= c <= h):
            raise DataQualityError("OHLC relationship invalid")

    @staticmethod
    def validate_change_pct(payload: dict) -> None:
        prev_close = payload["prev_close"]
        if prev_close <= 0:
            raise DataQualityError("prev_close must be positive")
        computed = round((payload["close"] - prev_close) / prev_close * 100, 2)
        if abs(computed - payload["change_pct"]) > 0.6:
            raise DataQualityError("change_pct inconsistent")

    @classmethod
    def validate_kline_daily(cls, payload: dict) -> None:
        cls.validate_required(
            payload,
            ["stock_code", "trade_date", "open", "high", "low", "close", "prev_close", "change_pct"],
        )
        if not isinstance(payload["trade_date"], date):
            raise DataQualityError("trade_date invalid")
        cls.validate_ohlc(payload)
        cls.validate_change_pct(payload)

    @classmethod
    def validate_kline_15m(cls, payload: dict) -> None:
        cls.validate_required(
            payload,
            ["stock_code", "trade_time", "open", "high", "low", "close", "prev_close", "change_pct"],
        )
        if not isinstance(payload["trade_time"], datetime):
            raise DataQualityError("trade_time invalid")
        cls.validate_ohlc(payload)
        cls.validate_change_pct(payload)

    @staticmethod
    def ensure_no_duplicate_daily(db: Session, stock_code: str, trade_date: date) -> None:
        if (
            db.query(MktStockKlineDaily)
            .filter(MktStockKlineDaily.stock_code == stock_code, MktStockKlineDaily.trade_date == trade_date)
            .first()
        ):
            raise DataQualityError("duplicate daily kline")

    @staticmethod
    def ensure_no_duplicate_15m(db: Session, stock_code: str, trade_time: datetime) -> None:
        if (
            db.query(MktStockKline15m)
            .filter(MktStockKline15m.stock_code == stock_code, MktStockKline15m.kline_time == trade_time)
            .first()
        ):
            raise DataQualityError("duplicate intraday kline")

    @staticmethod
    def log_task_error(db: Session, task_name: str, started_at: datetime, error_message: str) -> None:
        db.add(
            ConfigTaskLog(
                task_name=task_name,
                run_status="failed",
                started_at=started_at,
                finished_at=datetime.utcnow(),
                error_message=error_message,
                affected_rows=0,
            )
        )
        db.commit()
