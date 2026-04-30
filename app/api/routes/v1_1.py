from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import (
    DailyTradePlan,
    DailyTradePlanItem,
    MonthlyReview,
    SellPlan,
    SystemTaskLog,
    TradeExecutionChecklist,
    TradeRecord,
    TradeReviewDetail,
    UserTradingScore,
    WatchPool,
    WatchPoolScore,
    WeeklyReview,
)
from app.services.v1_1 import (
    ASSISTANT_NOTE,
    DailyTradePlanService,
    DisciplineRuleService,
    MonthlyReviewService,
    NotificationService,
    SellPlanService,
    StrictModeService,
    TradeChecklistService,
    TradeErrorTagService,
    TradeReviewDetailService,
    UnplannedTradeService,
    V11TaskService,
    WatchLifecycleService,
    WatchPoolRemovalService,
    WatchScoreService,
    WeeklyReviewService,
)

router = APIRouter(prefix="/v1", tags=["v1.1"])


def _guard(call):
    try:
        return call()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/watch-pool")
def list_v11_watch_pool(
    layer: str | None = None,
    status: str | None = None,
    entry_source: str | None = None,
    sector: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(WatchPool)
    if layer:
        query = query.filter(WatchPool.pool_layer == layer)
    if status:
        query = query.filter(WatchPool.lifecycle_status == status)
    if entry_source:
        query = query.filter(WatchPool.entry_source == entry_source)
    if sector:
        query = query.filter(WatchPool.sector_name == sector)
    return query.order_by(WatchPool.entry_score.desc().nullslast()).all()


@router.get("/watch-pool/layers")
def get_watch_layers(db: Session = Depends(get_db)):
    rows = db.query(WatchPool).all()
    return {
        layer: [item for item in rows if item.pool_layer == layer]
        for layer in ["L1_core", "L2_watch", "L3_candidate", "L4_archive"]
    }


@router.get("/watch-pool/scores")
def list_watch_scores(trade_date: date | None = None, db: Session = Depends(get_db)):
    query = db.query(WatchPoolScore)
    if trade_date:
        query = query.filter(WatchPoolScore.trade_date == trade_date)
    return query.order_by(WatchPoolScore.total_score.desc()).all()


@router.post("/watch-pool/score-candidates")
def score_candidates(payload: dict | None = None, db: Session = Depends(get_db)):
    trade_date = (payload or {}).get("trade_date") or date.today()
    return WatchScoreService(db).batch_score_candidates(trade_date)


@router.get("/watch-pool/archive")
def list_archive(db: Session = Depends(get_db)):
    return db.query(WatchPool).filter(WatchPool.pool_layer == "L4_archive").all()


@router.get("/watch-pool/{stock_code}/score")
def get_watch_score(stock_code: str, db: Session = Depends(get_db)):
    return (
        db.query(WatchPoolScore)
        .filter(WatchPoolScore.stock_code == stock_code)
        .order_by(WatchPoolScore.trade_date.desc())
        .first()
    )


@router.get("/watch-pool/{stock_code}/lifecycle")
def get_lifecycle(stock_code: str, db: Session = Depends(get_db)):
    return {
        "current_status": WatchLifecycleService(db).get_current_status(stock_code),
        "history": WatchLifecycleService(db).get_lifecycle_history(stock_code),
    }


@router.post("/watch-pool/{stock_code}/transition")
def transition_watch(stock_code: str, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: WatchLifecycleService(db).transition(stock_code, payload["to_status"], payload.get("reason", ""), payload.get("operator_type", "system"), payload.get("snapshot")))


@router.post("/watch-pool/{stock_code}/archive")
def archive_watch(stock_code: str, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: WatchLifecycleService(db).archive_stock(stock_code, payload.get("reason", "archive")))


@router.post("/watch-pool/{stock_code}/blacklist")
def blacklist_watch(stock_code: str, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: WatchLifecycleService(db).blacklist_stock(stock_code, payload.get("reason", "blacklist")))


@router.post("/watch-pool/{stock_code}/restore")
def restore_watch(stock_code: str, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: WatchLifecycleService(db).restore_to_watching(stock_code, payload.get("reason", "restore")))


@router.post("/watch-pool/evaluate-removal")
def evaluate_removal(payload: dict | None = None, db: Session = Depends(get_db)):
    return WatchPoolRemovalService(db).batch_evaluate_removal((payload or {}).get("trade_date") or date.today())


@router.post("/watch-pool/{stock_code}/downgrade")
def downgrade_watch(stock_code: str, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: WatchPoolRemovalService(db).downgrade_stock(stock_code, payload.get("reason", "downgrade")))


@router.post("/watch-pool/{stock_code}/remove-to-archive")
def remove_to_archive(stock_code: str, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: WatchPoolRemovalService(db).remove_to_archive(stock_code, payload.get("reason", "remove")))


@router.get("/discipline/rules")
def list_rules(db: Session = Depends(get_db)):
    return DisciplineRuleService(db).init_default_rules()


@router.patch("/discipline/rules/{rule_id}")
def update_rule(rule_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: DisciplineRuleService(db).update_rule(rule_id, payload))


@router.get("/discipline/evaluate")
def evaluate_discipline(position_ratio: float = 0.0, stop_loss_price: float | None = None, plan_item_id: int | None = None, db: Session = Depends(get_db)):
    return DisciplineRuleService(db).evaluate_rules({"position_ratio": position_ratio, "stop_loss_price": stop_loss_price, "plan_item_id": plan_item_id})


@router.post("/discipline/strict-mode")
def set_discipline_strict(payload: dict, db: Session = Depends(get_db)):
    return DisciplineRuleService(db).set_strict_mode(bool(payload.get("enabled")))


@router.get("/strict-mode")
def get_strict_mode(db: Session = Depends(get_db)):
    return StrictModeService(db).get_strict_mode_status()


@router.post("/strict-mode/enable")
def enable_strict_mode(db: Session = Depends(get_db)):
    return StrictModeService(db).enable_strict_mode()


@router.post("/strict-mode/disable")
def disable_strict_mode(db: Session = Depends(get_db)):
    return StrictModeService(db).disable_strict_mode()


@router.post("/strict-mode/evaluate")
def evaluate_strict(payload: dict, db: Session = Depends(get_db)):
    return StrictModeService(db).evaluate_trade_confirmation(payload)


@router.get("/daily-plans/today")
def get_today_plan(db: Session = Depends(get_db)):
    return DailyTradePlanService(db).get_plan(date.today()) or DailyTradePlanService(db).generate_plan(date.today())


@router.get("/daily-plans/{trade_date}")
def get_plan(trade_date: date, db: Session = Depends(get_db)):
    return DailyTradePlanService(db).get_plan(trade_date)


@router.post("/daily-plans/generate")
def generate_plan(payload: dict | None = None, db: Session = Depends(get_db)):
    return DailyTradePlanService(db).generate_plan((payload or {}).get("trade_date") or date.today())


@router.post("/daily-plans/{plan_id}/items")
def add_plan_item(plan_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: DailyTradePlanService(db).add_plan_item(plan_id, payload))


@router.get("/daily-plans/{plan_id}/items")
def list_plan_items(plan_id: int, db: Session = Depends(get_db)):
    return (
        db.query(DailyTradePlanItem)
        .filter(DailyTradePlanItem.plan_id == plan_id)
        .order_by(DailyTradePlanItem.item_id.asc())
        .all()
    )


@router.patch("/daily-plans/items/{item_id}")
def update_plan_item(item_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: DailyTradePlanService(db).update_plan_item(item_id, payload))


@router.post("/daily-plans/items/{item_id}/cancel")
def cancel_plan_item(item_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: DailyTradePlanService(db).cancel_plan_item(item_id, payload.get("reason", "cancelled")))


@router.post("/daily-plans/items/{item_id}/trigger")
def trigger_plan_item(item_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: DailyTradePlanService(db).trigger_plan_item(item_id, payload))


@router.post("/daily-plans/items/{item_id}/invalidate")
def invalidate_plan_item(item_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: DailyTradePlanService(db).mark_item_invalid(item_id, payload.get("reason", "invalid")))


@router.post("/daily-plans/{plan_id}/complete")
def complete_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(DailyTradePlan).filter(DailyTradePlan.plan_id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")
    return DailyTradePlanService(db).complete_plan_after_close(plan.trade_date)


@router.post("/trade-checklists/build")
def build_checklist(payload: dict, db: Session = Depends(get_db)):
    return TradeChecklistService(db).build_checklist(payload.get("signal_id"), payload.get("plan_item_id"), payload)


@router.get("/trade-checklists/{checklist_id}")
def get_checklist(checklist_id: int, db: Session = Depends(get_db)):
    return db.query(TradeExecutionChecklist).filter(TradeExecutionChecklist.checklist_id == checklist_id).first()


@router.post("/trade-checklists/{checklist_id}/confirm")
def confirm_checklist(checklist_id: int, db: Session = Depends(get_db)):
    return _guard(lambda: TradeChecklistService(db).confirm(checklist_id))


@router.get("/trades/unplanned")
def list_unplanned(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    return UnplannedTradeService(db).get_unplanned_trades(start_date, end_date)


@router.post("/trades/{trade_id}/mark-unplanned")
def mark_unplanned(trade_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: UnplannedTradeService(db).mark_unplanned_trade(trade_id, payload.get("reason", "manual")))


@router.get("/trades/unplanned/stats")
def unplanned_stats(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    return UnplannedTradeService(db).calculate_unplanned_trade_stats(start_date, end_date)


@router.get("/sell-plans")
def list_sell_plans(db: Session = Depends(get_db)):
    return SellPlanService(db).get_active_sell_plans()


@router.get("/trades/{trade_id}/sell-plans")
def list_trade_sell_plans(trade_id: int, db: Session = Depends(get_db)):
    return db.query(SellPlan).filter(SellPlan.trade_id == trade_id).all()


@router.post("/trades/{trade_id}/sell-plans/generate")
def generate_sell_plans(trade_id: int, db: Session = Depends(get_db)):
    return _guard(lambda: SellPlanService(db).generate_sell_plan_for_trade(trade_id))


@router.post("/sell-plans/{sell_plan_id}/trigger")
def trigger_sell_plan(sell_plan_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: SellPlanService(db).trigger_sell_plan(sell_plan_id, payload))


@router.post("/sell-plans/{sell_plan_id}/confirm")
def confirm_sell_plan(sell_plan_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: SellPlanService(db).confirm_sell_plan(sell_plan_id, payload))


@router.post("/sell-plans/{sell_plan_id}/cancel")
def cancel_sell_plan(sell_plan_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: SellPlanService(db).cancel_sell_plan(sell_plan_id, payload.get("reason", "cancel")))


@router.get("/trades/{trade_id}/review-detail")
def get_review_detail(trade_id: int, db: Session = Depends(get_db)):
    return db.query(TradeReviewDetail).filter(TradeReviewDetail.trade_id == trade_id).first()


@router.post("/trades/{trade_id}/review-detail/generate")
def generate_review_detail(trade_id: int, db: Session = Depends(get_db)):
    return _guard(lambda: TradeReviewDetailService(db).generate_review_detail(trade_id))


@router.patch("/trades/{trade_id}/review-detail")
def save_review_detail(trade_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: TradeReviewDetailService(db).save_user_review(trade_id, payload))


@router.post("/trades/{trade_id}/review-detail/error-tags")
def attach_review_tags(trade_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: TradeReviewDetailService(db).attach_error_tags(trade_id, payload.get("tag_ids", [])))


@router.post("/trades/{trade_id}/review-detail/complete")
def complete_review_detail(trade_id: int, db: Session = Depends(get_db)):
    return _guard(lambda: TradeReviewDetailService(db).mark_review_completed(trade_id))


@router.get("/error-tags")
def list_error_tags(db: Session = Depends(get_db)):
    return TradeErrorTagService(db).init_default_error_tags()


@router.post("/error-tags")
def create_error_tag(payload: dict, db: Session = Depends(get_db)):
    return TradeErrorTagService(db).create_error_tag(payload)


@router.patch("/error-tags/{tag_id}")
def update_error_tag(tag_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: TradeErrorTagService(db).update_error_tag(tag_id, payload))


@router.delete("/error-tags/{tag_id}")
def delete_error_tag(tag_id: int, db: Session = Depends(get_db)):
    TradeErrorTagService(db).delete_error_tag(tag_id)
    return {"message": "ok"}


@router.get("/error-tags/stats")
def error_stats(db: Session = Depends(get_db)):
    return TradeErrorTagService(db).calculate_error_stats()


@router.get("/error-tags/repeated-alerts")
def repeated_alerts(lookback_trades: int = 5, threshold: int = 3, db: Session = Depends(get_db)):
    return TradeErrorTagService(db).detect_repeated_errors(lookback_trades, threshold)


@router.get("/reviews/weekly")
def list_weekly_reviews(db: Session = Depends(get_db)):
    return db.query(WeeklyReview).order_by(WeeklyReview.week_start.desc()).all()


@router.post("/reviews/weekly/generate")
def generate_weekly_review(payload: dict, db: Session = Depends(get_db)):
    return WeeklyReviewService(db).generate_weekly_review(payload["week_start"], payload["week_end"])


@router.get("/reviews/weekly/{weekly_review_id}")
def get_weekly_review(weekly_review_id: int, db: Session = Depends(get_db)):
    return db.query(WeeklyReview).filter(WeeklyReview.weekly_review_id == weekly_review_id).first()


@router.patch("/reviews/weekly/{weekly_review_id}")
def patch_weekly_review(weekly_review_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: WeeklyReviewService(db).save_user_weekly_summary(weekly_review_id, payload))


@router.get("/reviews/weekly/{weekly_review_id}/suggestions")
def weekly_suggestions(weekly_review_id: int):
    return {"suggestions": [f"下周只交易今日计划内标的。{ASSISTANT_NOTE}"]}


@router.get("/reviews/monthly")
def get_monthly_review(month: str = Query(...), db: Session = Depends(get_db)):
    return db.query(MonthlyReview).filter(MonthlyReview.month == month).first()


@router.post("/reviews/monthly/generate")
def generate_monthly_review(payload: dict, db: Session = Depends(get_db)):
    return MonthlyReviewService(db).generate_monthly_review(payload["month"])


@router.get("/reviews/monthly/{monthly_review_id}")
def get_monthly_review_by_id(monthly_review_id: int, db: Session = Depends(get_db)):
    return db.query(MonthlyReview).filter(MonthlyReview.monthly_review_id == monthly_review_id).first()


@router.patch("/reviews/monthly/{monthly_review_id}")
def patch_monthly_review(monthly_review_id: int, payload: dict, db: Session = Depends(get_db)):
    return _guard(lambda: MonthlyReviewService(db).save_user_monthly_summary(monthly_review_id, payload))


@router.get("/trading-score/monthly")
def monthly_score(month: str = Query(...), db: Session = Depends(get_db)):
    return db.query(UserTradingScore).filter(UserTradingScore.period_type == "monthly", UserTradingScore.period_key == month).first()


@router.get("/notifications")
def list_notifications(unread: bool = False, db: Session = Depends(get_db)):
    return NotificationService(db).list_notifications({"unread": unread})


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    return _guard(lambda: NotificationService(db).mark_read(notification_id))


@router.post("/notifications/daily-plan/{plan_id}")
def notify_daily_plan(plan_id: int, db: Session = Depends(get_db)):
    return _guard(lambda: NotificationService(db).build_daily_plan_message(plan_id))


@router.post("/notifications/review-reminder")
def notify_review_reminder(payload: dict, db: Session = Depends(get_db)):
    return NotificationService(db).build_review_reminder(payload.get("type", "review_reminder"), payload.get("target_id", 0))


@router.post("/admin/tasks/{task_name}/run")
def run_v11_task(task_name: str, db: Session = Depends(get_db)):
    return V11TaskService(db).run_task(task_name)


@router.get("/admin/tasks/v1-1/logs")
def list_v11_task_logs(db: Session = Depends(get_db)):
    return (
        db.query(SystemTaskLog)
        .filter(SystemTaskLog.task_name.like("%v1_1%") | SystemTaskLog.task_name.like("%daily_trade_plan%") | SystemTaskLog.task_name.like("%monthly_review%"))
        .order_by(SystemTaskLog.started_at.desc())
        .limit(100)
        .all()
    )
