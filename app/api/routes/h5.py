from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_login
from app.api.response import ok, page
from app.core.database import get_db
from app.models import (
    MktDaily,
    ConfigNotificationRecord,
    MyNotificationSetting,
    MyUserPreference,
    MyUserProfile,
    PlanDaily,
    ReviewForm,
    ReviewMonthly,
    ReviewTrade,
    ReviewWeekly,
    WatchPool,
    WatchPoolStatusLog,
    WatchSignal,
    WatchSignalPerformance,
    WatchTrade,
    WatchTradeExecution,
)
from app.services.normalization import xueqiu_link
from app.services.prd_v1 import ASSISTANT_NOTE, PrdMarketDataService, PrdWatchPoolService, SeedService

router = APIRouter(prefix="/h5", tags=["h5"])


def _watch_dict(row: WatchPool) -> dict:
    return {
        "watch_id": row.id,
        "stock_code": row.stock_code,
        "stock_name": row.stock_name,
        "sector_name": row.sector_name,
        "labels": row.labels,
        "pool_status": row.pool_status,
        "monitor_enabled": row.monitor_enabled,
        "operation_strategies": row.operation_strategies,
        "buy_point_types": row.buy_point_types,
        "source_platform": row.source_platform,
        "source_rank": row.source_rank,
        "source_score": row.source_score,
        "source_reason": row.source_reason,
        "risk_note": ASSISTANT_NOTE,
        "xueqiu_url": row.xueqiu_url or xueqiu_link(row.stock_code),
    }


def _signal_dict(row: WatchSignal) -> dict:
    return {
        "signal_id": row.signal_id,
        "watch_id": row.watch_id,
        "stock_code": row.stock_code,
        "stock_name": row.stock_name,
        "signal_type": row.signal_type,
        "buy_point_type": row.buy_point_type,
        "strategy_name": row.strategy_name,
        "signal_level": row.signal_level,
        "trigger_time": row.trigger_time,
        "trigger_date": row.trigger_date,
        "trigger_price": row.trigger_price,
        "trigger_reason": row.trigger_reason,
        "risk_desc": row.risk_desc,
        "stop_loss_price": row.stop_loss_price,
        "target_price": row.target_price,
        "invalid_condition": row.invalid_condition,
        "signal_status": row.signal_status,
        "user_action": row.user_action,
        "assistant_note": ASSISTANT_NOTE,
    }


def _trade_dict(row: WatchTrade) -> dict:
    return {
        "trade_id": row.id,
        "signal_id": row.signal_id,
        "watch_id": row.watch_id,
        "stock_code": row.stock_code,
        "stock_name": row.stock_name,
        "trade_source": row.trade_source,
        "first_buy_time": row.first_buy_time,
        "first_buy_price": row.first_buy_price,
        "total_buy_amount": row.total_buy_amount,
        "average_buy_price": row.average_buy_price,
        "total_sell_amount": row.total_sell_amount,
        "remaining_amount": row.remaining_amount,
        "position_ratio": row.position_ratio,
        "stop_loss_price": row.stop_loss_price,
        "target_price": row.target_price,
        "pnl_amount": row.pnl_amount,
        "pnl_ratio": row.pnl_ratio,
        "holding_days": row.holding_days,
        "trade_status": row.trade_status,
        "closed_at": row.closed_at,
        "assistant_note": ASSISTANT_NOTE,
    }


def _execution_dict(row: WatchTradeExecution) -> dict:
    return {
        "execution_id": row.id,
        "trade_id": row.trade_id,
        "signal_id": row.signal_id,
        "watch_id": row.watch_id,
        "stock_code": row.stock_code,
        "stock_name": row.stock_name,
        "execution_type": row.execution_type,
        "execution_time": row.execution_time,
        "execution_price": row.execution_price,
        "execution_amount": row.execution_amount,
        "execution_reason": row.execution_reason,
        "pnl_amount": row.pnl_amount,
        "pnl_ratio": row.pnl_ratio,
        "is_full_exit": row.is_full_exit,
    }


def _review_dict(row: ReviewForm) -> dict:
    return {
        "review_id": row.id,
        "review_type": row.review_type,
        "review_period": row.review_period,
        "status": row.status,
        "title": row.title,
        "system_summary": row.system_summary,
        "user_summary": row.user_summary,
        "improvement_plan": row.improvement_plan,
        "payload": row.payload,
        "assistant_note": ASSISTANT_NOTE,
    }


@router.get("/market/trading-dates")
def trading_dates(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    query = db.query(MktDaily.trade_date).distinct()
    if start_date:
        query = query.filter(MktDaily.trade_date >= start_date)
    if end_date:
        query = query.filter(MktDaily.trade_date <= end_date)
    rows = query.order_by(MktDaily.trade_date.desc()).limit(120).all()
    return ok([row[0].isoformat() for row in rows])


@router.get("/market/overview")
def market_overview(trade_date: date, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(PrdMarketDataService(db).get_market_overview(trade_date))


@router.get("/market/hot-boards")
def hot_boards(trade_date: date | None = None, platform: str | None = None, page_no: int = 1, page_size: int = 20, db: Session = Depends(get_db), user=Depends(require_login)):
    rows = PrdMarketDataService(db).get_hot_boards(trade_date, platform)
    return ok(page(rows[(page_no - 1) * page_size : page_no * page_size], page_no, page_size, len(rows)))


@router.get("/market/hot-stocks")
def hot_stocks(trade_date: date | None = None, platform: str | None = None, page_no: int = 1, page_size: int = 20, db: Session = Depends(get_db), user=Depends(require_login)):
    rows = PrdMarketDataService(db).get_hot_stocks(trade_date, platform)
    return ok(page(rows[(page_no - 1) * page_size : page_no * page_size], page_no, page_size, len(rows)))


@router.get("/market/limit-ups")
def limit_ups(trade_date: date | None = None, platform: str | None = None, page_no: int = 1, page_size: int = 20, db: Session = Depends(get_db), user=Depends(require_login)):
    rows = PrdMarketDataService(db).get_limit_ups(trade_date, platform)
    return ok(page(rows[(page_no - 1) * page_size : page_no * page_size], page_no, page_size, len(rows)))


@router.get("/market/stocks/{stock_code}/source-summary")
def source_summary(stock_code: str, trade_date: date, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(PrdMarketDataService(db).get_stock_source_summary(stock_code, trade_date))


@router.get("/market/stocks/{stock_code}/latest-source")
def latest_source(stock_code: str, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(PrdMarketDataService(db).get_latest_source(stock_code))


@router.get("/market/stocks/{stock_code}/kline-daily")
def stock_kline_daily(stock_code: str, limit: int = 60, db: Session = Depends(get_db), user=Depends(require_login)):
    from app.services.kline import KlineService
    rows = KlineService(db).get_daily_kline(stock_code, limit)
    return ok([{
        "trade_date": r.trade_date.isoformat() if r.trade_date else None,
        "open": r.open_price,
        "high": r.high_price,
        "low": r.low_price,
        "close": r.close_price,
        "volume": r.volume,
    } for r in rows])


@router.get("/watch-pool")
def list_watch_pool(pool_status: str | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok([_watch_dict(row) for row in PrdWatchPoolService(db).list_watch_pool(pool_status)])


@router.get("/watch-pool/summary")
def watch_summary(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(PrdWatchPoolService(db).summary())


@router.get("/watch-pool/{watch_id}")
def get_watch(watch_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(_watch_dict(PrdWatchPoolService(db).get_watch(watch_id)))


@router.post("/watch-pool")
def add_watch(payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    try:
        return ok(_watch_dict(PrdWatchPoolService(db).add_watch(payload)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/watch-pool/{watch_id}")
def update_watch(watch_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(_watch_dict(PrdWatchPoolService(db).update_watch(watch_id, payload)))


@router.delete("/watch-pool/{watch_id}")
def remove_watch(watch_id: int, remove_reason: str = "用户剔除", db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(_watch_dict(PrdWatchPoolService(db).remove_watch(watch_id, remove_reason)))


@router.post("/watch-pool/{watch_id}/restore")
def restore_watch(watch_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(_watch_dict(PrdWatchPoolService(db).restore_watch(watch_id)))


@router.post("/watch-pool/{watch_id}/blacklist")
def blacklist_watch(watch_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(_watch_dict(PrdWatchPoolService(db).blacklist_watch(watch_id, payload.get("reason", "用户加入黑名单"))))


@router.post("/watch-pool/{watch_id}/unblacklist")
def unblacklist_watch(watch_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(_watch_dict(PrdWatchPoolService(db).unblacklist_watch(watch_id, payload.get("reason", "用户移出黑名单"))))


@router.post("/watch-pool/{watch_id}/monitor/enable")
def enable_monitor(watch_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(_watch_dict(PrdWatchPoolService(db).set_monitor(watch_id, True)))


@router.post("/watch-pool/{watch_id}/monitor/disable")
def disable_monitor(watch_id: int, payload: dict | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(_watch_dict(PrdWatchPoolService(db).set_monitor(watch_id, False, (payload or {}).get("reason", ""))))


@router.get("/watch-pool/{watch_id}/status-logs")
def watch_logs(watch_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    return ok([
        {
            "id": row.id,
            "watch_id": row.watch_id,
            "stock_code": row.stock_code,
            "from_status": row.from_status,
            "to_status": row.to_status,
            "change_reason": row.change_reason,
            "operator_type": row.operator_type,
            "operated_at": row.operated_at,
        }
        for row in PrdWatchPoolService(db).logs(watch_id)
    ])


@router.get("/watch-signals")
def list_watch_signals(signal_type: str | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    query = db.query(WatchSignal)
    if signal_type:
        query = query.filter(WatchSignal.signal_type == signal_type)
    rows = query.order_by(WatchSignal.trigger_time.desc()).limit(100).all()
    return ok([_signal_dict(row) for row in rows])


@router.get("/watch-signals/recent")
def recent_watch_signals(limit: int = 10, db: Session = Depends(get_db), user=Depends(require_login)):
    rows = db.query(WatchSignal).order_by(WatchSignal.trigger_time.desc()).limit(min(limit, 50)).all()
    return ok([_signal_dict(row) for row in rows])


@router.get("/watch-signals/summary")
def watch_signal_summary(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok({
        "total": db.query(WatchSignal).count(),
        "buy": db.query(WatchSignal).filter(WatchSignal.signal_type == "buy").count(),
        "sell_or_risk": db.query(WatchSignal).filter(WatchSignal.signal_type != "buy").count(),
        "assistant_note": ASSISTANT_NOTE,
    })


@router.get("/watch-signals/{signal_id}")
def get_watch_signal(signal_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(WatchSignal).filter(WatchSignal.signal_id == signal_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="signal not found")
    return ok(_signal_dict(row))


@router.post("/watch-signals/{signal_id}/ignore")
def ignore_watch_signal(signal_id: int, payload: dict | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(WatchSignal).filter(WatchSignal.signal_id == signal_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="signal not found")
    if row.user_action not in ["confirmed_buy", "false_positive"]:
        row.signal_status = "ignored"
        row.user_action = "ignored"
        row.handled_at = row.handled_at or datetime.utcnow()
        db.commit()
    return ok(_signal_dict(row))


@router.post("/watch-signals/{signal_id}/mark-false-positive")
def mark_false_positive(signal_id: int, payload: dict | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(WatchSignal).filter(WatchSignal.signal_id == signal_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="signal not found")
    row.signal_status = "false_positive"
    row.user_action = "false_positive"
    row.handled_at = datetime.utcnow()
    row.raw_snapshot = {**(row.raw_snapshot or {}), "false_positive_reason": (payload or {}).get("reason", "")}
    db.commit()
    return ok(_signal_dict(row))


@router.post("/watch-signals/{signal_id}/invalidate")
def invalidate_signal(signal_id: int, payload: dict | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(WatchSignal).filter(WatchSignal.signal_id == signal_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="signal not found")
    row.signal_status = "invalid"
    row.user_action = "invalid"
    row.handled_at = datetime.utcnow()
    row.invalid_condition = (payload or {}).get("reason", row.invalid_condition)
    db.commit()
    return ok(_signal_dict(row))


@router.get("/watch-signals/{signal_id}/performance")
def signal_performance(signal_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(WatchSignalPerformance).filter(WatchSignalPerformance.signal_id == signal_id).first()
    return ok({} if row is None else {
        "signal_id": row.signal_id,
        "follow_return_1d": row.follow_return_1d,
        "follow_return_3d": row.follow_return_3d,
        "follow_return_5d": row.follow_return_5d,
        "follow_return_10d": row.follow_return_10d,
        "is_confirmed_trade": row.is_confirmed_trade,
        "related_trade_id": row.related_trade_id,
    })


@router.post("/watch-signals/{signal_id}/confirm-buy")
def confirm_buy(signal_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    signal = db.query(WatchSignal).filter(WatchSignal.signal_id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="signal not found")
    existing_by_signal = db.query(WatchTrade).filter(WatchTrade.signal_id == signal_id).first()
    if existing_by_signal:
        return ok(_trade_dict(existing_by_signal), message="signal already confirmed")
    buy_price = float(payload["buy_price"])
    amount = float(payload["amount"])
    trade = (
        db.query(WatchTrade)
        .filter(WatchTrade.stock_code == signal.stock_code, WatchTrade.trade_status.in_(["open", "partial_sold", "holding"]))
        .first()
    )
    now = datetime.utcnow()
    if not trade:
        trade = WatchTrade(
            signal_id=signal.signal_id,
            watch_id=signal.watch_id,
            stock_code=signal.stock_code,
            stock_name=signal.stock_name,
            buy_point_type=signal.buy_point_type,
            first_buy_time=now,
            first_buy_price=buy_price,
            total_buy_amount=amount,
            remaining_amount=amount,
            average_buy_price=buy_price,
            position_ratio=payload.get("position_ratio"),
            stop_loss_price=payload.get("stop_loss_price"),
            target_price=payload.get("target_price"),
            trade_status="open",
            remark=payload.get("remark", ""),
        )
        db.add(trade)
        db.flush()
    else:
        total_cost = (trade.average_buy_price or 0) * trade.total_buy_amount + buy_price * amount
        trade.total_buy_amount += amount
        trade.remaining_amount += amount
        trade.average_buy_price = total_cost / trade.total_buy_amount if trade.total_buy_amount else buy_price
    db.add(WatchTradeExecution(
        trade_id=trade.id,
        signal_id=signal.signal_id,
        watch_id=signal.watch_id,
        stock_code=signal.stock_code,
        stock_name=signal.stock_name,
        execution_type="buy",
        execution_time=now,
        execution_price=buy_price,
        execution_amount=amount,
        execution_reason=payload.get("execution_reason", "user confirmed buy"),
    ))
    signal.signal_status = "confirmed_buy"
    signal.user_action = "confirmed_buy"
    signal.handled_at = now
    signal.related_trade_id = trade.id
    if signal.watch_id:
        watch = db.query(WatchPool).filter(WatchPool.id == signal.watch_id).first()
        if watch:
            old_status = watch.pool_status
            watch.pool_status = "holding"
            watch.monitor_enabled = False
            db.add(WatchPoolStatusLog(watch_id=watch.id, stock_code=watch.stock_code, from_status=old_status, to_status="holding", change_reason="user confirmed buy", operator_type="user"))
    perf = db.query(WatchSignalPerformance).filter(WatchSignalPerformance.signal_id == signal.signal_id).first()
    if not perf:
        db.add(WatchSignalPerformance(signal_id=signal.signal_id, watch_id=signal.watch_id, stock_code=signal.stock_code, trigger_price=signal.trigger_price, is_confirmed_trade=True, related_trade_id=trade.id))
    else:
        perf.is_confirmed_trade = True
        perf.related_trade_id = trade.id
    db.commit()
    db.refresh(trade)
    return ok(_trade_dict(trade))


@router.get("/watch-trades")
def list_watch_trades(status: str | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    query = db.query(WatchTrade)
    if status:
        query = query.filter(WatchTrade.trade_status == status)
    return ok([_trade_dict(row) for row in query.order_by(WatchTrade.created_at.desc()).limit(100).all()])


@router.get("/watch-trades/recent")
def recent_watch_trades(limit: int = 10, db: Session = Depends(get_db), user=Depends(require_login)):
    rows = db.query(WatchTrade).order_by(WatchTrade.created_at.desc()).limit(min(limit, 50)).all()
    return ok([_trade_dict(row) for row in rows])


@router.get("/watch-trades/summary")
def watch_trade_summary(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok({
        "total": db.query(WatchTrade).count(),
        "open": db.query(WatchTrade).filter(WatchTrade.trade_status.in_(["open", "partial_sold", "holding"])).count(),
        "completed": db.query(WatchTrade).filter(WatchTrade.trade_status == "completed").count(),
    })


@router.get("/watch-trades/{trade_id}")
def get_watch_trade(trade_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(WatchTrade).filter(WatchTrade.id == trade_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="trade not found")
    return ok(_trade_dict(row))


@router.get("/watch-trades/{trade_id}/executions")
def trade_executions(trade_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    rows = db.query(WatchTradeExecution).filter(WatchTradeExecution.trade_id == trade_id).order_by(WatchTradeExecution.execution_time.asc()).all()
    return ok([_execution_dict(row) for row in rows])


@router.post("/watch-trades/{trade_id}/confirm-sell")
def confirm_sell(trade_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    trade = db.query(WatchTrade).filter(WatchTrade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="trade not found")
    sell_price = float(payload["sell_price"])
    amount = float(payload["amount"])
    execution_type = payload.get("execution_type", "sell")
    execution_time = datetime.fromisoformat(payload["execution_time"]) if payload.get("execution_time") else datetime.utcnow()
    duplicate = (
        db.query(WatchTradeExecution)
        .filter(WatchTradeExecution.trade_id == trade_id, WatchTradeExecution.execution_time == execution_time, WatchTradeExecution.execution_type == execution_type)
        .first()
    )
    if duplicate:
        return ok(_execution_dict(duplicate), message="duplicate execution ignored")
    amount = min(amount, trade.remaining_amount)
    buy_price = trade.average_buy_price or trade.first_buy_price or sell_price
    pnl_amount = (sell_price - buy_price) * amount
    pnl_ratio = (sell_price - buy_price) / buy_price if buy_price else 0.0
    is_full_exit = bool(payload.get("is_full_exit")) or amount >= trade.remaining_amount
    execution = WatchTradeExecution(
        trade_id=trade.id,
        signal_id=trade.signal_id,
        watch_id=trade.watch_id,
        stock_code=trade.stock_code,
        stock_name=trade.stock_name,
        execution_type=execution_type,
        execution_time=execution_time,
        execution_price=sell_price,
        execution_amount=amount,
        execution_reason=payload.get("execution_reason", "user confirmed sell"),
        pnl_amount=pnl_amount,
        pnl_ratio=pnl_ratio,
        is_full_exit=is_full_exit,
    )
    db.add(execution)
    trade.total_sell_amount += amount
    trade.remaining_amount = max(0.0, trade.remaining_amount - amount)
    trade.pnl_amount += pnl_amount
    trade.pnl_ratio = trade.pnl_amount / ((trade.average_buy_price or buy_price) * trade.total_buy_amount) if trade.total_buy_amount else 0.0
    if trade.first_buy_time:
        trade.holding_days = max(0, (execution_time.date() - trade.first_buy_time.date()).days)
    if is_full_exit or trade.remaining_amount <= 0:
        trade.remaining_amount = 0
        trade.trade_status = "completed"
        trade.closed_at = execution_time
        if not db.query(ReviewTrade).filter(ReviewTrade.trade_id == trade.id).first():
            db.add(ReviewTrade(trade_id=trade.id, final_pnl_ratio=trade.pnl_ratio, status="pending"))
    else:
        trade.trade_status = "partial_sold"
    db.commit()
    db.refresh(execution)
    return ok(_execution_dict(execution))


@router.post("/watch-trades/{trade_id}/cancel")
def cancel_trade(trade_id: int, payload: dict | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    trade = db.query(WatchTrade).filter(WatchTrade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="trade not found")
    trade.trade_status = "cancelled"
    trade.close_reason = (payload or {}).get("reason", "cancelled by user")
    db.commit()
    return ok(_trade_dict(trade))


@router.post("/watch-trades/{trade_id}/close")
def close_trade(trade_id: int, payload: dict | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    trade = db.query(WatchTrade).filter(WatchTrade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="trade not found")
    trade.trade_status = "completed"
    trade.closed_at = datetime.utcnow()
    trade.close_reason = (payload or {}).get("reason", "closed by user")
    if not db.query(ReviewTrade).filter(ReviewTrade.trade_id == trade.id).first():
        db.add(ReviewTrade(trade_id=trade.id, final_pnl_ratio=trade.pnl_ratio, status="pending"))
    db.commit()
    return ok(_trade_dict(trade))


@router.put("/watch-trades/{trade_id}")
def update_trade(trade_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    trade = db.query(WatchTrade).filter(WatchTrade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="trade not found")
    for key in ["position_ratio", "stop_loss_price", "target_price", "remark"]:
        if key in payload:
            setattr(trade, key, payload[key])
    db.commit()
    return ok(_trade_dict(trade))


def _ensure_review_form(db: Session, review_type: str, review_period: str, title: str) -> ReviewForm:
    row = db.query(ReviewForm).filter_by(review_type=review_type, review_period=review_period).first()
    if row:
        return row
    row = ReviewForm(review_type=review_type, review_period=review_period, title=title, system_summary=ASSISTANT_NOTE)
    db.add(row)
    db.flush()
    return row


@router.get("/reviews")
def list_reviews(review_type: str | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    query = db.query(ReviewForm)
    if review_type:
        query = query.filter(ReviewForm.review_type == review_type)
    rows = query.order_by(ReviewForm.created_at.desc()).limit(100).all()
    return ok([_review_dict(row) for row in rows])


@router.get("/reviews/todos")
def review_todos(db: Session = Depends(get_db), user=Depends(require_login)):
    rows = db.query(ReviewForm).filter(ReviewForm.status.in_(["pending", "editing", "待填写", "填写中"])).all()
    return ok([_review_dict(row) for row in rows])


@router.get("/reviews/summary")
def review_summary(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok({
        "total": db.query(ReviewForm).count(),
        "pending": db.query(ReviewForm).filter(ReviewForm.status.in_(["pending", "待填写"])).count(),
        "completed": db.query(ReviewForm).filter(ReviewForm.status.in_(["completed", "已完成"])).count(),
    })


@router.get("/reviews/weekly")
def weekly_reviews(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok([_review_dict(row) for row in db.query(ReviewForm).filter_by(review_type="weekly").order_by(ReviewForm.review_period.desc()).all()])


@router.get("/reviews/monthly")
def monthly_reviews(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok([_review_dict(row) for row in db.query(ReviewForm).filter_by(review_type="monthly").order_by(ReviewForm.review_period.desc()).all()])


@router.get("/reviews/trade")
def trade_reviews(db: Session = Depends(get_db), user=Depends(require_login)):
    rows = db.query(ReviewTrade).order_by(ReviewTrade.created_at.desc()).limit(100).all()
    return ok([{"trade_review_id": row.id, "trade_id": row.trade_id, "status": row.status, "issue_tags": row.issue_tags, "trade_score": row.trade_score, "assistant_note": ASSISTANT_NOTE} for row in rows])


@router.get("/reviews/{review_id}")
def get_review(review_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(ReviewForm).filter(ReviewForm.id == review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="review not found")
    return ok(_review_dict(row))


@router.put("/reviews/{review_id}")
def save_review(review_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(ReviewForm).filter(ReviewForm.id == review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="review not found")
    for key in ["user_summary", "improvement_plan", "payload"]:
        if key in payload:
            setattr(row, key, payload[key])
    row.status = payload.get("status", "editing")
    db.commit()
    return ok(_review_dict(row))


@router.post("/reviews/{review_id}/complete")
def complete_review(review_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(ReviewForm).filter(ReviewForm.id == review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="review not found")
    row.status = "completed"
    db.commit()
    return ok(_review_dict(row))


@router.post("/reviews/{review_id}/archive")
def archive_review(review_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(ReviewForm).filter(ReviewForm.id == review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="review not found")
    row.status = "archived"
    db.commit()
    return ok(_review_dict(row))


@router.get("/reviews/weekly/{review_id}")
def get_weekly_review(review_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    return get_review(review_id, db, user)


@router.get("/reviews/monthly/{review_id}")
def get_monthly_review(review_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    return get_review(review_id, db, user)


@router.get("/reviews/trade/{trade_review_id}")
def get_trade_review(trade_review_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(ReviewTrade).filter(ReviewTrade.id == trade_review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="trade review not found")
    return ok({"trade_review_id": row.id, "trade_id": row.trade_id, "status": row.status, "issue_tags": row.issue_tags, "attribution_type": row.attribution_type, "user_comment": row.user_comment, "improvement_action": row.improvement_action, "trade_score": row.trade_score, "assistant_note": ASSISTANT_NOTE})


@router.put("/reviews/trade/{trade_review_id}")
def save_trade_review(trade_review_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(ReviewTrade).filter(ReviewTrade.id == trade_review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="trade review not found")
    for key in ["issue_tags", "attribution_type", "user_comment", "improvement_action", "trade_score"]:
        if key in payload:
            setattr(row, key, payload[key])
    row.status = payload.get("status", "editing")
    db.commit()
    return ok({"trade_review_id": row.id, "trade_id": row.trade_id, "status": row.status})


@router.post("/reviews/trade/{trade_review_id}/complete")
def complete_trade_review(trade_review_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(ReviewTrade).filter(ReviewTrade.id == trade_review_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="trade review not found")
    row.status = "completed"
    db.commit()
    return ok({"trade_review_id": row.id, "status": row.status})


@router.get("/me/profile")
def get_profile(db: Session = Depends(get_db), user=Depends(require_login)):
    SeedService(db).init_defaults()
    profile = db.query(MyUserProfile).first()
    return ok({"nickname": profile.nickname, "avatar_url": profile.avatar_url, "bio": profile.bio})


@router.put("/me/profile")
def update_profile(payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    SeedService(db).init_defaults()
    profile = db.query(MyUserProfile).first()
    for key in ["nickname", "avatar_url", "bio"]:
        if key in payload:
            setattr(profile, key, payload[key])
    db.commit()
    return ok({"nickname": profile.nickname, "avatar_url": profile.avatar_url, "bio": profile.bio})


@router.get("/me/preferences")
def get_preferences(preference_type: str | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    query = db.query(MyUserPreference)
    if preference_type:
        query = query.filter(MyUserPreference.preference_type == preference_type)
    return ok([{"preference_type": row.preference_type, "preference_key": row.preference_key, "preference_value": row.preference_value} for row in query.all()])


@router.put("/me/preferences")
def save_preference(payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(MyUserPreference).filter_by(preference_type=payload["preference_type"], preference_key=payload["preference_key"]).first()
    if not row:
        row = MyUserPreference(preference_type=payload["preference_type"], preference_key=payload["preference_key"])
        db.add(row)
    row.preference_value = payload.get("preference_value") or {}
    db.commit()
    return ok({"saved": True})


@router.get("/me/notification-settings")
def notification_settings(db: Session = Depends(get_db), user=Depends(require_login)):
    SeedService(db).init_defaults()
    return ok([{"push_type": row.push_type, "channel": row.channel, "enabled": row.enabled, "quiet_time": row.quiet_time} for row in db.query(MyNotificationSetting).all()])


@router.put("/me/notification-settings")
def save_notification_settings(payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(MyNotificationSetting).filter_by(push_type=payload["push_type"], channel=payload.get("channel", "site")).first()
    if not row:
        row = MyNotificationSetting(push_type=payload["push_type"], channel=payload.get("channel", "site"))
        db.add(row)
    row.enabled = bool(payload.get("enabled", True))
    row.quiet_time = payload.get("quiet_time") or {}
    db.commit()
    return ok({"saved": True})


@router.get("/me/todos")
def my_todos(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok({"pending_reviews": 0, "unread_notifications": db.query(ConfigNotificationRecord).filter(ConfigNotificationRecord.send_status == "unread").count()})


@router.get("/me/system-summary")
def my_system_summary(db: Session = Depends(get_db), user=Depends(require_login)):
    last_mkt = db.query(MktDaily).order_by(MktDaily.collected_at.desc()).first()
    last_collect = last_mkt.collected_at.isoformat() if last_mkt else None
    return ok({
        "mode": "single-user",
        "assistant_note": ASSISTANT_NOTE,
        "watch_count": db.query(WatchPool).count(),
        "last_collect_time": last_collect,
    })


@router.get("/me/backend-entry")
def backend_entry(user=Depends(require_login)):
    return ok({"enabled": True, "entry_url": "/admin", "label": "后台管理"})


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok([{"notification_id": row.record_id, "push_type": row.push_type, "title": row.title, "content": row.content, "send_status": row.send_status, "created_at": row.created_at} for row in db.query(ConfigNotificationRecord).order_by(ConfigNotificationRecord.created_at.desc()).limit(100).all()])


@router.get("/notifications/unread-count")
def unread_count(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok({"count": db.query(ConfigNotificationRecord).filter(ConfigNotificationRecord.send_status == "unread").count()})


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(ConfigNotificationRecord).filter(ConfigNotificationRecord.record_id == notification_id).first()
    if row:
        row.send_status = "read"
        db.commit()
    return ok({"read": True})


@router.post("/notifications/read-all")
def read_all_notifications(db: Session = Depends(get_db), user=Depends(require_login)):
    db.query(ConfigNotificationRecord).filter(ConfigNotificationRecord.send_status == "unread").update({"send_status": "read"})
    db.commit()
    return ok({"read_all": True})


@router.delete("/notifications/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(ConfigNotificationRecord).filter(ConfigNotificationRecord.record_id == notification_id).first()
    if row:
        db.delete(row)
        db.commit()
    return ok({"deleted": True})


@router.post("/me/collect-market")
def collect_market_now(db: Session = Depends(get_db), user=Depends(require_login)):
    from app.services.tasks import TaskService
    svc = TaskService(db)
    today = date.today()
    results = {}
    for task_name, fn in [
        ("collect_market_daily", svc.collect_market_daily),
        ("collect_hot_sector_rank", svc.collect_hot_sector_rank),
        ("collect_hot_stock_rank", svc.collect_hot_stock_rank),
        ("collect_limit_up_daily", svc.collect_limit_up_daily),
    ]:
        log = fn(today)
        results[task_name] = {"status": log.run_status, "affected_rows": log.affected_rows}
    return ok({"collect_time": datetime.utcnow().isoformat(), "results": results})


# ── Daily Plan ──

@router.get("/plans")
def list_plans(db: Session = Depends(get_db), user=Depends(require_login)):
    rows = db.query(PlanDaily).order_by(PlanDaily.plan_date.desc()).limit(60).all()
    return ok([
        {
            "id": row.id,
            "plan_date": row.plan_date.isoformat(),
            "today_position": row.today_position,
            "operation_summary": row.operation_summary,
            "execution_status": row.execution_status,
            "tomorrow_plan": row.tomorrow_plan,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ])


@router.post("/plans")
def create_plan(payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    plan_date_str = payload.get("plan_date") or date.today().isoformat()
    plan_date_val = date.fromisoformat(plan_date_str) if isinstance(plan_date_str, str) else date.today()
    existing = db.query(PlanDaily).filter(PlanDaily.plan_date == plan_date_val).first()
    if existing:
        for key in ["today_position", "operation_summary", "execution_status", "tomorrow_plan"]:
            if key in payload:
                setattr(existing, key, payload[key])
        db.commit()
        return ok({"id": existing.id, "plan_date": existing.plan_date.isoformat(), "updated": True})
    row = PlanDaily(
        plan_date=plan_date_val,
        today_position=payload.get("today_position", ""),
        operation_summary=payload.get("operation_summary", ""),
        execution_status=payload.get("execution_status", ""),
        tomorrow_plan=payload.get("tomorrow_plan", ""),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok({"id": row.id, "plan_date": row.plan_date.isoformat(), "created": True})


@router.put("/plans/{plan_id}")
def update_plan(plan_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(PlanDaily).filter(PlanDaily.id == plan_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="plan not found")
    for key in ["today_position", "operation_summary", "execution_status", "tomorrow_plan"]:
        if key in payload:
            setattr(row, key, payload[key])
    db.commit()
    return ok({"id": row.id, "plan_date": row.plan_date.isoformat(), "updated": True})


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(PlanDaily).filter(PlanDaily.id == plan_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="plan not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": True})
