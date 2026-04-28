from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy.orm import Session

from app.models import DailyPlan, SignalRecord, TradeRecord, TradeReview


class ReviewService:
    def __init__(self, db: Session):
        self.db = db

    def list_daily_plans(self, start_date: date | None = None, end_date: date | None = None) -> list[DailyPlan]:
        query = self.db.query(DailyPlan)
        if start_date:
            query = query.filter(DailyPlan.plan_date >= start_date)
        if end_date:
            query = query.filter(DailyPlan.plan_date <= end_date)
        return query.order_by(DailyPlan.plan_date.desc(), DailyPlan.created_at.desc()).all()

    def create_daily_plan(self, payload: dict) -> DailyPlan:
        plan = DailyPlan(
            plan_date=payload["plan_date"],
            title=payload["title"],
            focus=payload.get("focus", ""),
            risk_rule=payload.get("risk_rule", ""),
            note=payload.get("note", ""),
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def generate_trade_review(self, trade_id: int) -> TradeReview:
        trade = self.db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
        if not trade:
            raise ValueError("trade not found")
        metrics = {
            "buy_price": trade.buy_price,
            "sell_price": trade.sell_price,
            "realized_pnl": trade.realized_pnl,
            "status": trade.status,
        }
        review = self.db.query(TradeReview).filter(TradeReview.trade_id == trade_id).first() or TradeReview(
            trade_id=trade_id
        )
        review.metrics = metrics
        review.system_summary = "复盘聚焦市场环境、买点质量、卖点执行与风险管理，仅作为交易辅助"
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def calculate_weekly_metrics(self, week_start: date, week_end: date) -> dict:
        start_dt = datetime.combine(week_start, time.min)
        end_dt = datetime.combine(week_end, time.max)
        trades = (
            self.db.query(TradeRecord)
            .filter(TradeRecord.created_at >= start_dt, TradeRecord.created_at <= end_dt)
            .all()
        )
        closed = [trade for trade in trades if trade.realized_pnl is not None]
        wins = [trade for trade in closed if trade.realized_pnl and trade.realized_pnl > 0]
        losses = [trade for trade in closed if trade.realized_pnl and trade.realized_pnl <= 0]
        total_pnl = round(sum(trade.realized_pnl or 0 for trade in closed), 2)
        signal_ids = [trade.signal_id for trade in trades]
        signals = self.db.query(SignalRecord).filter(SignalRecord.id.in_(signal_ids)).all() if signal_ids else []
        return {
            "total_trades": len(trades),
            "win_rate": round(len(wins) / len(closed), 2) if closed else 0,
            "profit_loss_ratio": round(
                (sum(trade.realized_pnl for trade in wins) / abs(sum(trade.realized_pnl for trade in losses)))
                if wins and losses and sum(trade.realized_pnl for trade in losses) != 0
                else 0,
                2,
            ),
            "total_pnl": total_pnl,
            "max_drawdown": min((trade.realized_pnl or 0 for trade in closed), default=0),
            "avg_profit": round(sum(trade.realized_pnl for trade in wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(trade.realized_pnl for trade in losses) / len(losses), 2) if losses else 0,
            "best_trade": max((trade.realized_pnl or 0 for trade in closed), default=0),
            "worst_trade": min((trade.realized_pnl or 0 for trade in closed), default=0),
            "signal_success_rate": round(len(wins) / len(signals), 2) if signals else 0,
            "plan_execution_rate": 1.0 if trades else 0,
        }

    def generate_weekly_review(self, week_start: date, week_end: date) -> TradeReview:
        metrics = self.calculate_weekly_metrics(week_start, week_end)
        review_trade_id = -int(week_start.strftime("%Y%m%d"))
        review = (
            self.db.query(TradeReview)
            .filter(
                TradeReview.review_type == "weekly",
                TradeReview.week_start == week_start,
                TradeReview.week_end == week_end,
            )
            .first()
            or TradeReview(
                trade_id=review_trade_id,
                review_type="weekly",
                week_start=week_start,
                week_end=week_end,
            )
        )
        review.metrics = metrics
        review.system_summary = "周复盘用于检视市场、板块、个股、买卖点和执行偏差，不构成收益承诺"
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def save_weekly_review_note(self, week_start: date, week_end: date, user_notes: str) -> TradeReview:
        review = self.generate_weekly_review(week_start, week_end)
        review.user_notes = user_notes
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review
