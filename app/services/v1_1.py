from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean

from sqlalchemy.orm import Session

from app.models import (
    DailyTradePlan,
    DailyTradePlanItem,
    DisciplineRule,
    HotStockRank,
    MarketDaily,
    MonthlyReview,
    NotificationRecord,
    SectorDaily,
    SellPlan,
    SignalRecord,
    SystemTaskLog,
    TradeErrorTag,
    TradeExecutionChecklist,
    TradeRecord,
    TradeReviewDetail,
    UserTradingScore,
    WatchPool,
    WatchPoolLifecycle,
    WatchPoolScore,
    WeeklyReview,
)

ASSISTANT_NOTE = "仅作为交易辅助，请结合个人交易计划确认。"
STRICT_RULE = "strict_mode"
BAD_MARKETS = {"退潮", "冰点", "forbidden"}
VALID_TRANSITIONS = {
    None: {"candidate_source", "initial_selected", "watching", "blacklist"},
    "candidate_source": {"initial_selected", "invalid", "blacklist"},
    "initial_selected": {"watching", "invalid", "blacklist"},
    "watching": {"focused", "invalid", "archived", "blacklist"},
    "focused": {"planned", "watching", "invalid", "archived", "blacklist"},
    "planned": {"bought", "watching", "invalid", "archived", "blacklist"},
    "bought": {"holding", "sold", "blacklist"},
    "holding": {"sold", "blacklist"},
    "sold": {"archived", "blacklist"},
    "invalid": {"archived", "watching", "blacklist"},
    "archived": {"watching", "blacklist"},
    "blacklist": {"watching"},
}


def _today() -> date:
    return date.today()


def _as_date(value: date | str | None) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return _today()


def _entry_level(total_score: float, risk_tags: list[str] | None = None) -> str:
    if risk_tags and any(tag in {"ST", "退市风险", "重大负面", "blacklist"} for tag in risk_tags):
        return "rejected"
    if total_score >= 85:
        return "core"
    if total_score >= 70:
        return "normal"
    if total_score >= 55:
        return "candidate"
    return "rejected"


def _pool_layer(entry_level: str, lifecycle_status: str = "watching") -> str:
    if lifecycle_status in {"archived", "invalid", "sold"}:
        return "L4_archive"
    return {
        "core": "L1_core",
        "normal": "L2_watch",
        "candidate": "L3_candidate",
        "rejected": "L4_archive",
    }.get(entry_level, "L2_watch")


class WatchLifecycleService:
    def __init__(self, db: Session):
        self.db = db

    def get_current_status(self, stock_code: str) -> str | None:
        item = self.db.query(WatchPool).filter(WatchPool.stock_code == stock_code).first()
        return item.lifecycle_status if item else None

    def validate_transition(self, from_status: str | None, to_status: str) -> bool:
        return to_status in VALID_TRANSITIONS.get(from_status, set())

    def transition(
        self,
        stock_code: str,
        to_status: str,
        reason: str,
        operator_type: str = "system",
        snapshot: dict | None = None,
    ) -> WatchPoolLifecycle:
        item = self.db.query(WatchPool).filter(WatchPool.stock_code == stock_code).first()
        from_status = item.lifecycle_status if item else None
        if item and item.lifecycle_status == "blacklist" and to_status != "watching":
            raise ValueError("blacklist stock cannot transition automatically")
        if not self.validate_transition(from_status, to_status):
            raise ValueError(f"invalid lifecycle transition: {from_status}->{to_status}")
        if item:
            item.lifecycle_status = to_status
            item.pool_layer = _pool_layer(item.entry_level or "normal", to_status)
            if to_status in {"archived", "invalid"}:
                item.archive_reason = reason
                item.archived_at = datetime.utcnow()
            if to_status == "blacklist":
                item.is_blacklist = True
                item.blacklist_reason = reason
        existing = (
            self.db.query(WatchPoolLifecycle)
            .filter(
                WatchPoolLifecycle.stock_code == stock_code,
                WatchPoolLifecycle.to_status == to_status,
                WatchPoolLifecycle.action_reason == reason,
            )
            .order_by(WatchPoolLifecycle.created_at.desc())
            .first()
        )
        if existing and (datetime.utcnow() - existing.created_at).total_seconds() < 3:
            self.db.commit()
            return existing
        record = WatchPoolLifecycle(
            stock_code=stock_code,
            stock_name=item.stock_name if item else None,
            from_status=from_status,
            to_status=to_status,
            action_type="transition",
            action_reason=reason,
            operator_type=operator_type,
            snapshot=snapshot or {"assistant_note": ASSISTANT_NOTE},
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_lifecycle_history(self, stock_code: str) -> list[WatchPoolLifecycle]:
        return (
            self.db.query(WatchPoolLifecycle)
            .filter(WatchPoolLifecycle.stock_code == stock_code)
            .order_by(WatchPoolLifecycle.created_at.asc())
            .all()
        )

    def archive_stock(self, stock_code: str, reason: str) -> WatchPoolLifecycle:
        return self.transition(stock_code, "archived", reason, operator_type="user")

    def blacklist_stock(self, stock_code: str, reason: str) -> WatchPoolLifecycle:
        return self.transition(stock_code, "blacklist", reason, operator_type="user")

    def restore_to_watching(self, stock_code: str, reason: str) -> WatchPoolLifecycle:
        item = self.db.query(WatchPool).filter(WatchPool.stock_code == stock_code).first()
        if item:
            item.is_blacklist = False
            item.blacklist_reason = None
        return self.transition(stock_code, "watching", reason, operator_type="user")


class WatchScoreService:
    def __init__(self, db: Session):
        self.db = db

    def calculate_watch_score(self, stock_code: str, trade_date: date | str) -> WatchPoolScore:
        d = _as_date(trade_date)
        item = self.db.query(WatchPool).filter(WatchPool.stock_code == stock_code).first()
        if item and item.is_blacklist:
            risk_tags = ["blacklist"]
        else:
            risk_tags = []
        market = self.db.query(MarketDaily).filter(MarketDaily.trade_date == d).first()
        hot = (
            self.db.query(HotStockRank)
            .filter(HotStockRank.trade_date == d, HotStockRank.stock_code == stock_code)
            .all()
        )
        sector = None
        if item and item.sector_name:
            sector = (
                self.db.query(SectorDaily)
                .filter(SectorDaily.trade_date == d, SectorDaily.sector_name == item.sector_name)
                .first()
            )
        market_score = min(max((market.market_score if market else 60.0), 0), 100)
        sector_score = min(max((sector.sector_score if sector else 60.0), 0), 100)
        hot_score = min(sum(row.total_score for row in hot), 100) if hot else 55.0
        technical_score = 70.0
        risk_score = 0.0 if risk_tags else 80.0
        liquidity_score = 70.0
        total_score = round(
            market_score * 0.15
            + sector_score * 0.25
            + hot_score * 0.15
            + technical_score * 0.20
            + risk_score * 0.15
            + liquidity_score * 0.10,
            2,
        )
        level = self.decide_entry_level(total_score, risk_tags)
        score = WatchPoolScore(
            stock_code=stock_code,
            trade_date=d,
            market_score=market_score,
            sector_score=sector_score,
            hot_score=hot_score,
            technical_score=technical_score,
            risk_score=risk_score,
            liquidity_score=liquidity_score,
            total_score=total_score,
            entry_level=level,
            score_detail={"risk_tags": risk_tags, "assistant_note": ASSISTANT_NOTE},
        )
        return score

    def save_watch_score(self, score: WatchPoolScore) -> WatchPoolScore:
        existing = (
            self.db.query(WatchPoolScore)
            .filter(WatchPoolScore.stock_code == score.stock_code, WatchPoolScore.trade_date == score.trade_date)
            .first()
        )
        if existing:
            for key in [
                "market_score",
                "sector_score",
                "hot_score",
                "technical_score",
                "risk_score",
                "liquidity_score",
                "total_score",
                "entry_level",
                "score_detail",
            ]:
                setattr(existing, key, getattr(score, key))
            saved = existing
        else:
            self.db.add(score)
            saved = score
        item = self.db.query(WatchPool).filter(WatchPool.stock_code == score.stock_code).first()
        if item:
            item.entry_score = score.total_score
            item.entry_level = score.entry_level
            item.pool_layer = self.decide_pool_layer(score.entry_level, item.lifecycle_status)
            item.next_action = self.explain_score(score)
        self.db.commit()
        self.db.refresh(saved)
        return saved

    def decide_entry_level(self, total_score: float, risk_tags: list[str] | None = None) -> str:
        return _entry_level(total_score, risk_tags)

    def decide_pool_layer(self, entry_level: str, lifecycle_status: str = "watching") -> str:
        return _pool_layer(entry_level, lifecycle_status)

    def explain_score(self, score: WatchPoolScore) -> str:
        return f"Watch Score {score.total_score}，等级 {score.entry_level}。{ASSISTANT_NOTE}"

    def batch_score_candidates(self, trade_date: date | str) -> list[WatchPoolScore]:
        saved = []
        for item in self.db.query(WatchPool).filter(WatchPool.active.is_(True)).all():
            if item.is_blacklist:
                continue
            saved.append(self.save_watch_score(self.calculate_watch_score(item.stock_code, trade_date)))
        return saved


class WatchPoolRemovalService:
    def __init__(self, db: Session):
        self.db = db
        self.lifecycle = WatchLifecycleService(db)

    def evaluate_removal(self, stock_code: str, trade_date: date | str) -> dict:
        item = self.db.query(WatchPool).filter(WatchPool.stock_code == stock_code).first()
        if not item:
            return {"should_remove": False, "reason": "not_found"}
        d = _as_date(trade_date)
        if item.observe_start_date and (d - item.observe_start_date).days > item.max_observe_days:
            return {"should_remove": True, "reason": "time: observation timeout"}
        if item.sector_status == "退潮":
            return {"should_remove": True, "reason": "sector: sector fading"}
        return {"should_remove": False, "reason": "still valid"}

    def batch_evaluate_removal(self, trade_date: date | str) -> list[dict]:
        results = []
        for item in self.db.query(WatchPool).filter(WatchPool.active.is_(True)).all():
            result = self.evaluate_removal(item.stock_code, trade_date)
            if result["should_remove"]:
                self.remove_to_archive(item.stock_code, result["reason"])
            results.append({"stock_code": item.stock_code, **result})
        return results

    def downgrade_stock(self, stock_code: str, reason: str):
        item = self.db.query(WatchPool).filter(WatchPool.stock_code == stock_code).first()
        if not item:
            raise ValueError("watch stock not found")
        item.pool_layer = "L3_candidate" if item.pool_layer == "L2_watch" else "L2_watch"
        item.next_action = f"降级观察：{reason}。{ASSISTANT_NOTE}"
        self.db.commit()
        return item

    def remove_to_archive(self, stock_code: str, reason: str):
        return self.lifecycle.archive_stock(stock_code, reason)

    def calculate_post_entry_performance(self, stock_code: str) -> dict:
        return {"stock_code": stock_code, "max_profit_ratio": 0.0, "max_loss_ratio": 0.0}

    def should_blacklist_after_review(self, stock_code: str) -> bool:
        return False


class DisciplineRuleService:
    DEFAULT_RULES = [
        ("max_daily_trades", "count", {"value": 2}, True),
        ("max_total_position", "position", {"value": 0.5}, True),
        ("max_single_position", "position", {"value": 0.2}, True),
        ("max_single_loss_ratio", "risk", {"value": 0.02}, True),
        ("max_consecutive_losses", "risk", {"value": 2}, False),
        ("forbid_chase_high", "risk", {"max_change_pct": 0.07}, False),
        ("forbid_unplanned_trade", "discipline", {"enabled": True}, True),
        ("require_stop_loss", "risk", {"enabled": True}, True),
        ("require_review_before_trade", "discipline", {"enabled": False}, False),
        ("market_score_min_for_new_plan", "market", {"value": 50}, True),
        (STRICT_RULE, "system", {"enabled": False}, False),
    ]

    def __init__(self, db: Session):
        self.db = db

    def init_default_rules(self) -> list[DisciplineRule]:
        created = []
        for name, rule_type, value, strict_required in self.DEFAULT_RULES:
            existing = self.db.query(DisciplineRule).filter(DisciplineRule.rule_name == name).first()
            if not existing:
                existing = DisciplineRule(
                    rule_name=name,
                    rule_type=rule_type,
                    rule_value=value,
                    strict_mode_required=strict_required,
                )
                self.db.add(existing)
                created.append(existing)
        self.db.commit()
        return self.list_rules()

    def list_rules(self) -> list[DisciplineRule]:
        return self.db.query(DisciplineRule).order_by(DisciplineRule.rule_id.asc()).all()

    def get_active_rules(self) -> dict:
        self.init_default_rules()
        return {rule.rule_name: rule for rule in self.db.query(DisciplineRule).filter(DisciplineRule.enabled.is_(True)).all()}

    def update_rule(self, rule_id: int, payload: dict) -> DisciplineRule:
        rule = self.db.query(DisciplineRule).filter(DisciplineRule.rule_id == rule_id).first()
        if not rule:
            raise ValueError("rule not found")
        for key in ["rule_value", "enabled", "strict_mode_required"]:
            if key in payload:
                setattr(rule, key, payload[key])
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def is_strict_mode_enabled(self) -> bool:
        self.init_default_rules()
        rule = self.db.query(DisciplineRule).filter(DisciplineRule.rule_name == STRICT_RULE).first()
        return bool(rule and rule.enabled and rule.rule_value.get("enabled"))

    def set_strict_mode(self, enabled: bool) -> DisciplineRule:
        self.init_default_rules()
        rule = self.db.query(DisciplineRule).filter(DisciplineRule.rule_name == STRICT_RULE).first()
        rule.enabled = True
        rule.rule_value = {"enabled": enabled}
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def evaluate_rules(self, context: dict) -> dict:
        rules = self.get_active_rules()
        failures = []
        if rules["require_stop_loss"].rule_value.get("enabled") and not context.get("stop_loss_price"):
            failures.append("未设置止损，不能确认交易")
        max_single = rules["max_single_position"].rule_value.get("value", 0.2)
        if float(context.get("position_ratio", 0) or 0) > max_single:
            failures.append("单笔仓位超过纪律规则")
        if self.is_strict_mode_enabled() and not context.get("plan_item_id"):
            failures.append("严格模式下计划外交易不能确认")
        return {"passed": not failures, "failed_items": failures, "assistant_note": ASSISTANT_NOTE}


class StrictModeService:
    def __init__(self, db: Session):
        self.rules = DisciplineRuleService(db)

    def enable_strict_mode(self):
        return self.rules.set_strict_mode(True)

    def disable_strict_mode(self):
        return self.rules.set_strict_mode(False)

    def get_strict_mode_status(self) -> dict:
        return {"enabled": self.rules.is_strict_mode_enabled(), "assistant_note": ASSISTANT_NOTE}

    def evaluate_trade_confirmation(self, payload: dict) -> dict:
        return self.rules.evaluate_rules(payload)

    def evaluate_plan_creation(self, payload: dict) -> dict:
        market_state = payload.get("market_state")
        blocked = market_state in BAD_MARKETS
        return {"allowed": not blocked, "reason": "市场退潮或冰点禁止新增买入计划" if blocked else "", "assistant_note": ASSISTANT_NOTE}

    def evaluate_signal_push(self, signal: SignalRecord | dict) -> dict:
        signal_type = signal.signal_type if hasattr(signal, "signal_type") else signal.get("signal_type")
        return {"allowed": signal_type != "buy" or True, "assistant_note": ASSISTANT_NOTE}

    def build_block_reason(self, context: dict) -> str:
        result = self.evaluate_trade_confirmation(context)
        return "；".join(result["failed_items"]) or ""


class DailyTradePlanService:
    def __init__(self, db: Session):
        self.db = db

    def _permission(self, market_state: str) -> str:
        if market_state in {"强势"}:
            return "tradable"
        if market_state in {"退潮", "冰点"}:
            return "forbidden"
        return "cautious"

    def generate_plan(self, trade_date: date | str) -> DailyTradePlan:
        d = _as_date(trade_date)
        existing = self.db.query(DailyTradePlan).filter(DailyTradePlan.trade_date == d).first()
        market = self.db.query(MarketDaily).filter(MarketDaily.trade_date == d).first()
        market_score = market.market_score if market else 60.0
        market_state = market.market_status if market else "震荡"
        sectors = (
            self.db.query(SectorDaily).filter(SectorDaily.trade_date == d).order_by(SectorDaily.sector_score.desc()).limit(3).all()
        )
        payload = {
            "market_score": market_score,
            "market_state": market_state,
            "trade_permission": self._permission(market_state),
            "max_total_position": 0.5 if market_score >= 65 else 0.3,
            "max_single_position": 0.2,
            "key_sectors": [
                {"sector_name": s.sector_name, "sector_score": s.sector_score, "risk_hint": s.risk_hint}
                for s in sectors
            ],
            "risk_summary": f"今日计划仅用于盘前准备，{ASSISTANT_NOTE}",
            "discipline_note": f"只交易计划内股票；未触发条件不买；跌破止损必须执行。{ASSISTANT_NOTE}",
            "plan_status": "active",
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            plan = existing
        else:
            plan = DailyTradePlan(trade_date=d, **payload)
            self.db.add(plan)
            self.db.flush()
        self.db.commit()
        self.db.refresh(plan)
        if plan.trade_permission != "forbidden":
            self._sync_watch_items(plan)
        return plan

    def _sync_watch_items(self, plan: DailyTradePlan) -> None:
        candidates = (
            self.db.query(WatchPool)
            .filter(
                WatchPool.active.is_(True),
                WatchPool.is_blacklist.is_(False),
                WatchPool.pool_layer.in_(["L1_core", "L2_watch"]),
            )
            .order_by(WatchPool.entry_score.desc().nullslast())
            .limit(5)
            .all()
        )
        for item in candidates:
            exists = (
                self.db.query(DailyTradePlanItem)
                .filter(DailyTradePlanItem.plan_id == plan.plan_id, DailyTradePlanItem.stock_code == item.stock_code)
                .first()
            )
            if not exists:
                self.db.add(
                    DailyTradePlanItem(
                        plan_id=plan.plan_id,
                        stock_code=item.stock_code,
                        stock_name=item.stock_name,
                        action_type="buy_watch",
                        trigger_condition=f"等待买入观察信号触发。{ASSISTANT_NOTE}",
                        expected_price_min=item.latest_price * 0.97 if item.latest_price else None,
                        expected_price_max=item.latest_price * 1.03 if item.latest_price else None,
                        stop_loss_price=item.latest_price * 0.95 if item.latest_price else None,
                        target_price=item.latest_price * 1.08 if item.latest_price else None,
                        position_ratio=0.1,
                        invalid_condition="市场退潮、板块退潮或个股风险提醒出现。",
                        source_type="watch_pool",
                        source_id=item.id,
                    )
                )
        self.db.commit()

    def refresh_plan_at_morning(self, trade_date): return self.generate_plan(trade_date)
    def refresh_plan_during_market(self, trade_date): return self.generate_plan(trade_date)

    def complete_plan_after_close(self, trade_date: date | str) -> DailyTradePlan:
        plan = self.get_plan(trade_date) or self.generate_plan(trade_date)
        plan.plan_status = "completed"
        plan.execution_summary = self.calculate_plan_execution_summary(plan.plan_id)
        self.db.commit()
        return plan

    def get_plan(self, trade_date: date | str) -> DailyTradePlan | None:
        return self.db.query(DailyTradePlan).filter(DailyTradePlan.trade_date == _as_date(trade_date)).first()

    def add_plan_item(self, plan_id: int, payload: dict) -> DailyTradePlanItem:
        item = DailyTradePlanItem(plan_id=plan_id, **payload)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update_plan_item(self, item_id: int, payload: dict) -> DailyTradePlanItem:
        item = self.db.query(DailyTradePlanItem).filter(DailyTradePlanItem.item_id == item_id).first()
        if not item:
            raise ValueError("plan item not found")
        for key, value in payload.items():
            if hasattr(item, key):
                setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def cancel_plan_item(self, item_id: int, reason: str): return self.update_plan_item(item_id, {"status": "cancelled", "user_note": reason})
    def trigger_plan_item(self, item_id: int, trigger_snapshot: dict): return self.update_plan_item(item_id, {"status": "triggered", "user_note": str(trigger_snapshot)})
    def execute_plan_item(self, item_id: int, trade_id: int): return self.update_plan_item(item_id, {"status": "executed", "source_id": trade_id})
    def mark_item_invalid(self, item_id: int, reason: str): return self.update_plan_item(item_id, {"status": "invalid", "user_note": reason})

    def calculate_plan_execution_summary(self, plan_id: int) -> dict:
        items = self.db.query(DailyTradePlanItem).filter(DailyTradePlanItem.plan_id == plan_id).all()
        executed = len([item for item in items if item.status == "executed"])
        return {"total_items": len(items), "executed_items": executed, "execution_rate": executed / len(items) if items else 0}


class TradeChecklistService:
    def __init__(self, db: Session):
        self.db = db

    def build_checklist(self, signal_id: int | None, plan_item_id: int | None, payload: dict) -> TradeExecutionChecklist:
        stock_code = payload.get("stock_code")
        signal = self.db.query(SignalRecord).filter(SignalRecord.id == signal_id).first() if signal_id else None
        if signal:
            stock_code = signal.stock_code
        context = {
            "plan_item_id": plan_item_id,
            "stop_loss_price": payload.get("stop_loss_price"),
            "position_ratio": payload.get("position_ratio", payload.get("position", 0)),
        }
        result = DisciplineRuleService(self.db).evaluate_rules(context)
        failed = list(result["failed_items"])
        checklist = TradeExecutionChecklist(
            signal_id=signal_id,
            plan_item_id=plan_item_id,
            stock_code=stock_code,
            trade_date=_as_date(payload.get("trade_date")),
            stop_loss_check=bool(payload.get("stop_loss_price")),
            position_size_check="单笔仓位超过纪律规则" not in failed,
            signal_check=bool(signal_id or payload.get("manual_reason")),
            all_passed=not failed,
            failed_items=failed,
        )
        checklist.market_check = payload.get("market_state") not in BAD_MARKETS
        if not checklist.market_check:
            checklist.failed_items.append("市场退潮或冰点，不通过买入前检查")
        checklist.all_passed = not checklist.failed_items
        self.db.add(checklist)
        self.db.commit()
        self.db.refresh(checklist)
        return checklist

    def evaluate_checklist(self, checklist: TradeExecutionChecklist) -> dict:
        return {"passed": checklist.all_passed, "failed_items": checklist.failed_items, "assistant_note": ASSISTANT_NOTE}

    def require_user_confirmation(self, checklist_id: int) -> TradeExecutionChecklist:
        checklist = self.db.query(TradeExecutionChecklist).filter(TradeExecutionChecklist.checklist_id == checklist_id).first()
        if not checklist:
            raise ValueError("checklist not found")
        return checklist

    def can_confirm_trade(self, checklist_id: int) -> bool:
        checklist = self.require_user_confirmation(checklist_id)
        return checklist.all_passed

    def confirm(self, checklist_id: int) -> TradeExecutionChecklist:
        checklist = self.require_user_confirmation(checklist_id)
        if not checklist.all_passed:
            raise ValueError("checklist failed")
        checklist.user_confirmed = True
        self.db.commit()
        return checklist

    def explain_failed_items(self, checklist: TradeExecutionChecklist) -> list[str]:
        return checklist.failed_items


class UnplannedTradeService:
    def __init__(self, db: Session):
        self.db = db

    def detect_unplanned_trade(self, payload: dict) -> dict:
        is_unplanned = not payload.get("signal_id") or not payload.get("plan_item_id")
        return {"is_unplanned": is_unplanned, "reason": "该交易不在今日交易计划内。" if is_unplanned else "", "assistant_note": ASSISTANT_NOTE}

    def mark_unplanned_trade(self, trade_id: int, reason: str) -> TradeRecord:
        trade = self.db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
        if not trade:
            raise ValueError("trade not found")
        trade.is_unplanned = True
        trade.discipline_flags = {"unplanned_reason": reason, "assistant_note": ASSISTANT_NOTE}
        self.db.commit()
        return trade

    def get_unplanned_trades(self, start_date: date | str | None, end_date: date | str | None) -> list[TradeRecord]:
        return self.db.query(TradeRecord).filter(TradeRecord.is_unplanned.is_(True)).all()

    def calculate_unplanned_trade_stats(self, start_date: date | str | None, end_date: date | str | None) -> dict:
        trades = self.get_unplanned_trades(start_date, end_date)
        return {"unplanned_trade_count": len(trades), "assistant_note": ASSISTANT_NOTE}


class SellPlanService:
    def __init__(self, db: Session):
        self.db = db

    def generate_sell_plan_for_trade(self, trade_id: int) -> list[SellPlan]:
        trade = self.db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
        if not trade:
            raise ValueError("trade not found")
        plans = []
        if trade.stop_loss_price:
            plans.append(self._upsert_plan(trade, "stop_loss", trade.stop_loss_price, "跌破止损价时执行人工确认卖出。"))
        if trade.target_price:
            plans.append(self._upsert_plan(trade, "take_profit", trade.target_price, "达到目标价时执行人工确认止盈。"))
        self.db.commit()
        return plans

    def _upsert_plan(self, trade: TradeRecord, sell_type: str, price: float, reason: str) -> SellPlan:
        existing = (
            self.db.query(SellPlan)
            .filter(SellPlan.trade_id == trade.id, SellPlan.sell_type == sell_type, SellPlan.status == "pending")
            .first()
        )
        if existing:
            return existing
        plan = SellPlan(
            trade_id=trade.id,
            sell_type=sell_type,
            planned_price=price,
            sell_reason=f"{reason}{ASSISTANT_NOTE}",
            sell_ratio=1.0,
        )
        self.db.add(plan)
        return plan

    def trigger_sell_plan(self, sell_plan_id: int, snapshot: dict) -> SellPlan:
        plan = self.db.query(SellPlan).filter(SellPlan.sell_plan_id == sell_plan_id).first()
        if not plan:
            raise ValueError("sell plan not found")
        plan.status = "triggered"
        plan.execution_comment = str(snapshot)
        self.db.commit()
        return plan

    def confirm_sell_plan(self, sell_plan_id: int, payload: dict) -> SellPlan:
        plan = self.db.query(SellPlan).filter(SellPlan.sell_plan_id == sell_plan_id).first()
        if not plan:
            raise ValueError("sell plan not found")
        trade = self.db.query(TradeRecord).filter(TradeRecord.id == plan.trade_id).first()
        quantity = int(payload.get("quantity") or payload.get("sell_amount") or trade.quantity)
        price = float(payload.get("price") or payload.get("sell_price") or plan.planned_price or trade.buy_price)
        plan.sell_price = price
        plan.sell_amount = quantity
        plan.user_confirmed = True
        plan.status = "executed"
        plan.pnl_amount = round((price - trade.buy_price) * quantity, 2)
        plan.pnl_ratio = round((price - trade.buy_price) / trade.buy_price, 4)
        trade.sell_price = price
        trade.sell_quantity = (trade.sell_quantity or 0) + quantity
        trade.sell_reason = payload.get("reason", plan.sell_reason)
        trade.sell_time = datetime.utcnow()
        trade.realized_pnl = (trade.realized_pnl or 0) + plan.pnl_amount
        trade.status = "closed" if trade.sell_quantity >= trade.quantity else "partial_sold"
        if trade.status == "closed":
            trade.review_status = "pending"
        self.db.commit()
        return plan

    def cancel_sell_plan(self, sell_plan_id: int, reason: str) -> SellPlan:
        plan = self.db.query(SellPlan).filter(SellPlan.sell_plan_id == sell_plan_id).first()
        if not plan:
            raise ValueError("sell plan not found")
        plan.status = "cancelled"
        plan.execution_comment = reason
        self.db.commit()
        return plan

    def get_active_sell_plans(self) -> list[SellPlan]:
        return self.db.query(SellPlan).filter(SellPlan.status.in_(["pending", "triggered"])).all()


class TradeReviewDetailService:
    def __init__(self, db: Session):
        self.db = db

    def generate_review_detail(self, trade_id: int) -> TradeReviewDetail:
        trade = self.db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
        if not trade:
            raise ValueError("trade not found")
        existing = self.db.query(TradeReviewDetail).filter(TradeReviewDetail.trade_id == trade_id).first()
        pnl_ratio = ((trade.sell_price or trade.buy_price) - trade.buy_price) / trade.buy_price if trade.buy_price else 0
        trade_score = max(0, min(100, 70 + pnl_ratio * 100))
        payload = {
            "buy_signal_valid": bool(trade.signal_id),
            "buy_plan_valid": not trade.is_unplanned,
            "entry_quality_score": 75 if not trade.is_unplanned else 55,
            "exit_quality_score": 70 if trade.sell_price else 0,
            "final_pnl_ratio": round(pnl_ratio, 4),
            "holding_days": 0,
            "risk_reward_actual": round(pnl_ratio / 0.02, 2) if pnl_ratio else 0,
            "stop_loss_executed": bool(trade.sell_price and trade.stop_loss_price and trade.sell_price <= trade.stop_loss_price),
            "target_executed": bool(trade.sell_price and trade.target_price and trade.sell_price >= trade.target_price),
            "plan_execution_result": "计划内" if not trade.is_unplanned else "计划外交易",
            "trade_score": round(trade_score, 2),
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            detail = existing
        else:
            detail = TradeReviewDetail(trade_id=trade_id, **payload)
            self.db.add(detail)
        trade.trade_score = payload["trade_score"]
        self.db.commit()
        self.db.refresh(detail)
        return detail

    def save_user_review(self, trade_id: int, payload: dict) -> TradeReviewDetail:
        detail = self.generate_review_detail(trade_id)
        detail.user_answers = payload.get("user_answers", detail.user_answers)
        detail.improvement_action = payload.get("improvement_action", detail.improvement_action)
        self.db.commit()
        return detail

    def attach_error_tags(self, trade_id: int, tag_ids: list[int]) -> TradeReviewDetail:
        detail = self.generate_review_detail(trade_id)
        tags = self.db.query(TradeErrorTag).filter(TradeErrorTag.tag_id.in_(tag_ids)).all()
        detail.error_tags = [{"tag_id": tag.tag_id, "tag_name": tag.tag_name} for tag in tags]
        self.db.commit()
        return detail

    def mark_review_completed(self, trade_id: int) -> TradeReviewDetail:
        detail = self.generate_review_detail(trade_id)
        trade = self.db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
        if trade:
            trade.review_status = "completed"
        self.db.commit()
        return detail


class TradeErrorTagService:
    DEFAULT_TAGS = ["追高买入", "左侧过早买入", "止损犹豫", "止盈贪婪", "卖飞恐惧", "报复交易", "计划外交易", "仓位过重", "频繁交易", "忽视市场", "忽视板块", "买入跟风股", "信号误判"]

    def __init__(self, db: Session):
        self.db = db

    def init_default_error_tags(self) -> list[TradeErrorTag]:
        for name in self.DEFAULT_TAGS:
            if not self.db.query(TradeErrorTag).filter(TradeErrorTag.tag_name == name).first():
                self.db.add(TradeErrorTag(tag_name=name, tag_type="discipline", description=f"{name}，{ASSISTANT_NOTE}"))
        self.db.commit()
        return self.list_error_tags()

    def list_error_tags(self) -> list[TradeErrorTag]:
        return self.db.query(TradeErrorTag).order_by(TradeErrorTag.tag_id.asc()).all()

    def create_error_tag(self, payload: dict) -> TradeErrorTag:
        tag = TradeErrorTag(**payload, is_system=False)
        self.db.add(tag)
        self.db.commit()
        return tag

    def update_error_tag(self, tag_id: int, payload: dict) -> TradeErrorTag:
        tag = self.db.query(TradeErrorTag).filter(TradeErrorTag.tag_id == tag_id).first()
        if not tag:
            raise ValueError("tag not found")
        for key, value in payload.items():
            if hasattr(tag, key):
                setattr(tag, key, value)
        self.db.commit()
        return tag

    def delete_error_tag(self, tag_id: int) -> None:
        tag = self.db.query(TradeErrorTag).filter(TradeErrorTag.tag_id == tag_id).first()
        if tag:
            self.db.delete(tag)
            self.db.commit()

    def calculate_error_stats(self, start_date=None, end_date=None) -> dict:
        stats: dict[str, int] = {}
        for detail in self.db.query(TradeReviewDetail).all():
            for tag in detail.error_tags or []:
                name = tag.get("tag_name", str(tag))
                stats[name] = stats.get(name, 0) + 1
        return stats

    def detect_repeated_errors(self, lookback_trades: int = 5, threshold: int = 3) -> list[dict]:
        stats = self.calculate_error_stats()
        return [
            {"message": f"你最近 {lookback_trades} 笔交易中，多次出现“{name}”。{ASSISTANT_NOTE}", "count": count}
            for name, count in stats.items()
            if count >= threshold
        ]


class WeeklyReviewService:
    def __init__(self, db: Session):
        self.db = db

    def generate_weekly_review(self, week_start: date | str, week_end: date | str) -> WeeklyReview:
        start, end = _as_date(week_start), _as_date(week_end)
        existing = self.db.query(WeeklyReview).filter(WeeklyReview.week_start == start, WeeklyReview.week_end == end).first()
        trades = self.db.query(TradeRecord).all()
        closed = [t for t in trades if t.realized_pnl is not None]
        pnl = [t.realized_pnl or 0 for t in closed]
        payload = {
            "total_trades": len(trades),
            "win_rate": len([x for x in pnl if x > 0]) / len(pnl) if pnl else 0,
            "total_pnl": round(sum(pnl), 2),
            "profit_loss_ratio": abs(mean([x for x in pnl if x > 0]) / mean([x for x in pnl if x < 0])) if [x for x in pnl if x > 0] and [x for x in pnl if x < 0] else 0,
            "expectancy": mean(pnl) if pnl else 0,
            "unplanned_trade_count": len([t for t in trades if t.is_unplanned]),
            "error_stats": TradeErrorTagService(self.db).calculate_error_stats(start, end),
            "market_summary": f"本周市场环境复盘。{ASSISTANT_NOTE}",
            "next_week_discipline": f"下周继续按今日计划和检查清单执行。{ASSISTANT_NOTE}",
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            review = existing
        else:
            review = WeeklyReview(week_start=start, week_end=end, **payload)
            self.db.add(review)
        self.db.commit()
        return review

    def save_user_weekly_summary(self, review_id: int, payload: dict) -> WeeklyReview:
        review = self.db.query(WeeklyReview).filter(WeeklyReview.weekly_review_id == review_id).first()
        if not review:
            raise ValueError("weekly review not found")
        review.user_summary = payload.get("user_summary", review.user_summary)
        self.db.commit()
        return review


class MonthlyReviewService:
    def __init__(self, db: Session):
        self.db = db

    def generate_monthly_review(self, month: str) -> MonthlyReview:
        existing = self.db.query(MonthlyReview).filter(MonthlyReview.month == month).first()
        trades = self.db.query(TradeRecord).all()
        pnl = [t.realized_pnl or 0 for t in trades if t.realized_pnl is not None]
        ability = self.calculate_ability_score(month)
        payload = {
            "monthly_pnl": round(sum(pnl), 2),
            "total_trades": len(trades),
            "win_rate": len([x for x in pnl if x > 0]) / len(pnl) if pnl else 0,
            "expectancy": mean(pnl) if pnl else 0,
            "discipline_score": ability["total_score"],
            "ability_score": ability,
            "top_errors": list(TradeErrorTagService(self.db).calculate_error_stats().items())[:5],
            "next_month_goals": {"goal": f"减少计划外交易。{ASSISTANT_NOTE}"},
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
            review = existing
        else:
            review = MonthlyReview(month=month, **payload)
            self.db.add(review)
        score = self.db.query(UserTradingScore).filter(UserTradingScore.period_type == "monthly", UserTradingScore.period_key == month).first()
        if not score:
            score = UserTradingScore(period_type="monthly", period_key=month)
            self.db.add(score)
        for key in ["stock_selection_score", "entry_score", "exit_score", "position_score", "risk_control_score", "execution_score", "review_score", "total_score"]:
            setattr(score, key, ability.get(key, 0))
        score.score_detail = ability
        self.db.commit()
        return review

    def calculate_ability_score(self, month: str) -> dict:
        base = {
            "stock_selection_score": 72,
            "entry_score": 70,
            "exit_score": 68,
            "position_score": 75,
            "risk_control_score": 74,
            "execution_score": 70,
            "review_score": 70,
        }
        base["total_score"] = round(mean(base.values()), 2)
        return base

    def save_user_monthly_summary(self, review_id: int, payload: dict) -> MonthlyReview:
        review = self.db.query(MonthlyReview).filter(MonthlyReview.monthly_review_id == review_id).first()
        if not review:
            raise ValueError("monthly review not found")
        review.next_month_goals = payload.get("next_month_goals", review.next_month_goals)
        self.db.commit()
        return review


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(self, notification_type: str, payload: dict) -> NotificationRecord:
        record = NotificationRecord(
            notification_type=notification_type,
            title=payload.get("title", notification_type),
            content=payload.get("content", ASSISTANT_NOTE),
            payload=payload,
        )
        self.db.add(record)
        self.db.commit()
        return record

    def list_notifications(self, filters: dict | None = None) -> list[NotificationRecord]:
        query = self.db.query(NotificationRecord).order_by(NotificationRecord.created_at.desc())
        if filters and filters.get("unread"):
            query = query.filter(NotificationRecord.is_read.is_(False))
        return query.all()

    def mark_read(self, notification_id: int) -> NotificationRecord:
        record = self.db.query(NotificationRecord).filter(NotificationRecord.notification_id == notification_id).first()
        if not record:
            raise ValueError("notification not found")
        record.is_read = True
        self.db.commit()
        return record

    def build_daily_plan_message(self, plan_id: int) -> NotificationRecord:
        plan = self.db.query(DailyTradePlan).filter(DailyTradePlan.plan_id == plan_id).first()
        if not plan:
            raise ValueError("plan not found")
        return self.create_notification(
            "daily_plan",
            {
                "title": "Aquant 今日交易计划",
                "content": f"日期：{plan.trade_date}\n市场状态：{plan.market_state}\n交易权限：{plan.trade_permission}\n今日纪律：只交易计划内股票；未触发条件不买；跌破止损必须执行。\n{ASSISTANT_NOTE}",
                "plan_id": plan_id,
            },
        )

    def build_unplanned_trade_message(self, trade_id: int) -> NotificationRecord:
        return self.create_notification("unplanned_trade", {"title": "计划外交易提醒", "content": f"该交易不在今日交易计划内。{ASSISTANT_NOTE}", "trade_id": trade_id})

    def build_repeated_error_message(self, stats: dict) -> NotificationRecord:
        return self.create_notification("repeated_error", {"title": "重复错误提醒", "content": f"检测到重复错误：{stats}。{ASSISTANT_NOTE}", "stats": stats})

    def build_review_reminder(self, notification_type: str, target_id: int) -> NotificationRecord:
        return self.create_notification(notification_type, {"title": "复盘提醒", "content": f"请完成复盘训练。{ASSISTANT_NOTE}", "target_id": target_id})


class V11TaskService:
    def __init__(self, db: Session):
        self.db = db

    def run_task(self, task_name: str) -> SystemTaskLog:
        started = datetime.utcnow()
        log = SystemTaskLog(task_name=task_name, status="running", started_at=started)
        self.db.add(log)
        self.db.commit()
        affected = 0
        try:
            if task_name == "generate_daily_trade_plan_task":
                DailyTradePlanService(self.db).generate_plan(_today())
                affected = 1
            elif task_name == "evaluate_watch_pool_lifecycle_task":
                affected = len(WatchPoolRemovalService(self.db).batch_evaluate_removal(_today()))
            elif task_name == "generate_weekly_review_v1_1_task":
                WeeklyReviewService(self.db).generate_weekly_review(_today() - timedelta(days=6), _today())
                affected = 1
            elif task_name == "generate_monthly_review_task":
                MonthlyReviewService(self.db).generate_monthly_review(_today().strftime("%Y-%m"))
                affected = 1
            elif task_name == "repeated_error_detection_task":
                alerts = TradeErrorTagService(self.db).detect_repeated_errors()
                for alert in alerts:
                    NotificationService(self.db).build_repeated_error_message(alert)
                affected = len(alerts)
            else:
                raise ValueError(f"unsupported v1.1 task: {task_name}")
            log.status = "success"
            log.affected_rows = affected
        except Exception as exc:
            log.status = "failed"
            log.error_message = str(exc)
        finally:
            log.finished_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(log)
        return log
