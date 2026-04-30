from datetime import date

from app.models import MarketDaily, SectorDaily, TradeRecord, WatchPool
from app.services.v1_1 import (
    ASSISTANT_NOTE,
    DailyTradePlanService,
    DisciplineRuleService,
    MonthlyReviewService,
    NotificationService,
    SellPlanService,
    TradeChecklistService,
    TradeErrorTagService,
    TradeReviewDetailService,
    UnplannedTradeService,
    WatchLifecycleService,
    WatchScoreService,
    WeeklyReviewService,
)


def seed_market(db_session):
    d = date(2026, 4, 30)
    db_session.add(
        MarketDaily(
            trade_date=d,
            sh_index=3100,
            sz_index=10000,
            cyb_index=2000,
            total_amount=1.2,
            up_count=3000,
            down_count=1800,
            flat_count=100,
            up_ratio=62,
            limit_up_count=80,
            limit_down_count=5,
            broken_limit_count=12,
            broken_limit_ratio=15,
            max_continue_board=5,
            market_score=82,
            market_status="强势",
        )
    )
    db_session.add(
        SectorDaily(
            trade_date=d,
            sector_name="机器人",
            change_pct=3.2,
            limit_up_count=8,
            leader_stock_code="603019.SH",
            leader_stock_name="中科曙光",
            sector_score=88,
            sector_type="主线板块",
            reason="主线扩散",
            risk_hint=ASSISTANT_NOTE,
        )
    )
    db_session.commit()
    return d


def seed_watch(db_session):
    item = WatchPool(
        stock_code="603019.SH",
        stock_name="中科曙光",
        sector_name="机器人",
        reason="主线核心候选",
        labels=["core"],
        latest_price=50,
        observe_start_date=date(2026, 4, 30),
        pool_layer="L1_core",
        entry_level="core",
        entry_score=90,
    )
    db_session.add(item)
    db_session.commit()
    return item


def test_v1_1_watch_score_plan_checklist_and_reviews(db_session):
    trade_date = seed_market(db_session)
    seed_watch(db_session)

    lifecycle = WatchLifecycleService(db_session).transition("603019.SH", "focused", "评分进入重点观察")
    assert lifecycle.to_status == "focused"
    assert WatchLifecycleService(db_session).get_current_status("603019.SH") == "focused"

    score = WatchScoreService(db_session).save_watch_score(
        WatchScoreService(db_session).calculate_watch_score("603019.SH", trade_date)
    )
    assert score.total_score >= 70
    assert score.entry_level in {"normal", "core"}

    plan = DailyTradePlanService(db_session).generate_plan(trade_date)
    assert plan.trade_permission == "tradable"
    items = db_session.query(type(DailyTradePlanService(db_session).add_plan_item)).all() if False else []
    assert plan.plan_id

    DisciplineRuleService(db_session).init_default_rules()
    failed = TradeChecklistService(db_session).build_checklist(
        None,
        None,
        {"stock_code": "603019.SH", "trade_date": trade_date.isoformat(), "position_ratio": 0.1},
    )
    assert not failed.all_passed
    assert "未设置止损" in "；".join(failed.failed_items)

    ok = TradeChecklistService(db_session).build_checklist(
        None,
        1,
        {
            "stock_code": "603019.SH",
            "trade_date": trade_date.isoformat(),
            "position_ratio": 0.1,
            "stop_loss_price": 48,
            "manual_reason": "买入观察信号",
        },
    )
    assert ok.all_passed

    trade = TradeRecord(
        signal_id=1,
        stock_code="603019.SH",
        stock_name="中科曙光",
        buy_price=50,
        quantity=100,
        position_ratio=0.1,
        stop_loss_price=48,
        target_price=56,
        trade_plan=ASSISTANT_NOTE,
        plan_id=plan.plan_id,
        plan_item_id=1,
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)

    sell_plans = SellPlanService(db_session).generate_sell_plan_for_trade(trade.id)
    assert {item.sell_type for item in sell_plans} == {"stop_loss", "take_profit"}
    SellPlanService(db_session).confirm_sell_plan(sell_plans[1].sell_plan_id, {"price": 56, "quantity": 100})
    db_session.refresh(trade)
    assert trade.status == "closed"

    detail = TradeReviewDetailService(db_session).generate_review_detail(trade.id)
    assert detail.trade_score > 70

    tags = TradeErrorTagService(db_session).init_default_error_tags()
    TradeReviewDetailService(db_session).attach_error_tags(trade.id, [tags[6].tag_id])
    stats = TradeErrorTagService(db_session).calculate_error_stats()
    assert "计划外交易" in stats

    weekly = WeeklyReviewService(db_session).generate_weekly_review(date(2026, 4, 24), trade_date)
    monthly = MonthlyReviewService(db_session).generate_monthly_review("2026-04")
    assert weekly.total_trades == 1
    assert monthly.total_trades == 1

    notice = NotificationService(db_session).build_daily_plan_message(plan.plan_id)
    assert ASSISTANT_NOTE in notice.content


def test_v1_1_strict_mode_blocks_unplanned_and_unplanned_stats(db_session):
    seed_market(db_session)
    DisciplineRuleService(db_session).init_default_rules()
    DisciplineRuleService(db_session).set_strict_mode(True)

    result = DisciplineRuleService(db_session).evaluate_rules({"position_ratio": 0.1, "stop_loss_price": 10})
    assert not result["passed"]
    assert "严格模式" in "；".join(result["failed_items"])

    trade = TradeRecord(
        signal_id=0,
        stock_code="000001.SZ",
        stock_name="平安银行",
        buy_price=10,
        quantity=100,
        position_ratio=0.1,
        stop_loss_price=9.8,
        target_price=11,
        trade_plan=ASSISTANT_NOTE,
        is_unplanned=True,
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)

    UnplannedTradeService(db_session).mark_unplanned_trade(trade.id, "手动临时记录")
    stats = UnplannedTradeService(db_session).calculate_unplanned_trade_stats(None, None)
    assert stats["unplanned_trade_count"] == 1
