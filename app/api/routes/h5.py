from __future__ import annotations

from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_login
from app.api.response import ok, page
from app.core.database import get_db
from app.models import (
    ConfigNotificationRecord,
    ConfigTask,
    ConfigTaskLog,
    MktDaily,
    MktStockQuote,
    MyNotificationSetting,
    MyUserPreference,
    MyUserProfile,
    PlanDaily,
    ReviewForm,
    ReviewMonthly,
    ReviewTrade,
    ReviewWeekly,
    TradingRuleDefinition,
    TradingSystemDefinition,
    TradingSystemParamDefinition,
    TradingSystemRuleBinding,
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


def _quote_payload(row: MktStockQuote | None) -> dict:
    if not row:
        return {"last_price": None, "price": None, "change_pct": None, "price_updated_at": None}
    return {
        "last_price": row.latest_price,
        "price": row.latest_price,
        "change_pct": row.change_pct,
        "price_updated_at": row.source_update_time.isoformat() if row.source_update_time else None,
    }


def _quote_map(db: Session, stock_codes: list[str]) -> dict[str, MktStockQuote]:
    codes = sorted({code for code in stock_codes if code})
    if not codes:
        return {}
    rows = db.query(MktStockQuote).filter(MktStockQuote.stock_code.in_(codes)).all()
    return {row.stock_code: row for row in rows}


def _watch_dict(row: WatchPool, quote: MktStockQuote | None = None, system_name: str | None = None) -> dict:
    system_code = row.trading_system_code or row.trading_system
    data = {
        "watch_id": row.id,
        "stock_code": row.stock_code,
        "stock_name": row.stock_name,
        "sector_name": row.sector_name,
        "labels": row.labels,
        "status": row.status,
        "entry_source": row.entry_source,
        "entry_reason": row.entry_reason,
        "trading_system": row.trading_system,
        "trading_system_code": row.trading_system_code,
        "trading_system_name": system_name or system_code,
        "system_stage": row.system_stage or "observe",
        "system_params_json": row.system_params_json or {},
        "active_rule_codes_json": row.active_rule_codes_json or [],
        "next_action": row.next_action,
        "system_recommendation": row.system_recommendation,
        "key_observe_price": row.key_observe_price,
        "auto_remove_price": row.auto_remove_price,
        "invalid_condition": row.invalid_condition,
        "risk_tags": row.risk_tags,
        "signal_enabled": row.signal_enabled,
        "latest_signal_id": row.latest_signal_id,
        "user_remark": row.user_remark,
        "monitor_enabled": row.monitor_enabled,
        "reason": row.reason,
        "operation_strategies": row.operation_strategies,
        "buy_point_types": row.buy_point_types,
        "entry_price": row.entry_price,
        "remark": row.remark,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "risk_note": ASSISTANT_NOTE,
    }
    data.update(_quote_payload(quote))
    return data


def _system_name_map(db: Session, system_codes: list[str | None]) -> dict[str, str]:
    codes = sorted({code for code in system_codes if code})
    if not codes:
        return {}
    rows = db.query(TradingSystemDefinition).filter(TradingSystemDefinition.system_code.in_(codes)).all()
    return {row.system_code: row.system_name for row in rows}


def _rule_map(db: Session, rule_codes: list[str | None]) -> dict[str, TradingRuleDefinition]:
    codes = sorted({code for code in rule_codes if code})
    if not codes:
        return {}
    rows = db.query(TradingRuleDefinition).filter(TradingRuleDefinition.rule_code.in_(codes)).all()
    return {row.rule_code: row for row in rows}


def _rule_payload(rule_code: str | None, rule: TradingRuleDefinition | None = None) -> dict | None:
    if not rule_code:
        return None
    return {
        "rule_code": rule_code,
        "rule_name": rule.rule_name if rule else rule_code,
        "rule_type": rule.rule_type if rule else None,
        "timeframe": rule.timeframe if rule else None,
        "executor_key": rule.executor_key if rule else None,
        "display_name": rule.rule_name if rule else rule_code,
    }


def _rule_payloads(rule_codes: list[str] | None, rule_map: dict[str, TradingRuleDefinition] | None = None) -> list[dict]:
    rule_map = rule_map or {}
    return [
        payload
        for payload in (_rule_payload(code, rule_map.get(code)) for code in (rule_codes or []))
        if payload
    ]


SAFE_RULE_EXECUTORS = {
    "always_false",
    "macd_bottom_divergence",
    "macd_top_divergence",
    "macd_dead_cross",
    "break_level",
    "break_ma",
    "pullback_to_level",
    "breakout_level",
    "volume_spike",
    "ma_trend",
    "profit_loss_threshold",
}


def _simplify_snapshot(snapshot: dict | None) -> dict:
    if not isinstance(snapshot, dict):
        return {}
    keys = [
        "latest_price",
        "latest_close",
        "latest_time",
        "timeframe",
        "rule_code",
        "executor_key",
        "bars_count",
        "last_macd",
        "last_dif",
        "last_dea",
    ]
    return {key: snapshot[key] for key in keys if key in snapshot}


def _evaluate_observe_rules(db: Session, watch: WatchPool, trade_date: date) -> dict:
    from app.providers.factory import ProviderFactory
    from app.rule_executors import RuleContext, get_executor
    from app.services.kline import KlineService

    if not watch.trading_system_code:
        raise HTTPException(status_code=400, detail="watch has no trading_system_code")

    kline_service = KlineService(db)
    provider = ProviderFactory.create()
    quote = db.query(MktStockQuote).filter(MktStockQuote.stock_code == watch.stock_code).first()

    def _provider_5m_bars(stock_code: str) -> list[SimpleNamespace]:
        if not hasattr(provider, "get_intraday_kline"):
            return []
        try:
            start_time = datetime.combine(trade_date, time(9, 30))
            end_time = datetime.combine(trade_date, time(15, 0))
            bars = []
            for item in provider.get_intraday_kline(stock_code, "5m", start_time, end_time) or []:
                bars.append(
                    SimpleNamespace(
                        close_price=item.get("close"),
                        volume=item.get("volume", 0.0),
                        kline_time=item.get("kline_time") or item.get("trade_time"),
                    )
                )
            return bars
        except Exception:
            return []

    def _rule_config(binding: TradingSystemRuleBinding, rule: TradingRuleDefinition) -> dict:
        config = {
            "binding_id": binding.binding_id,
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "rule_type": rule.rule_type,
            "timeframe": rule.timeframe,
            "executor_key": rule.executor_key,
            "required": binding.required,
            "logic_group": binding.logic_group,
            "logic_operator": binding.logic_operator,
            "config_json": binding.config_json or {},
        }
        if rule.executor_key == "macd_bottom_divergence":
            try:
                config["kline_bars"] = (
                    kline_service.get_15m_kline(watch.stock_code, 80)
                    if rule.timeframe == "15m"
                    else _provider_5m_bars(watch.stock_code)
                )
            except Exception:
                config["kline_bars"] = []
        return config

    bindings = (
        db.query(TradingSystemRuleBinding, TradingRuleDefinition)
        .join(TradingRuleDefinition, TradingRuleDefinition.rule_code == TradingSystemRuleBinding.rule_code)
        .filter(
            TradingSystemRuleBinding.system_code == watch.trading_system_code,
            TradingSystemRuleBinding.stage == "observe",
            TradingSystemRuleBinding.enabled.is_(True),
            TradingRuleDefinition.enabled.is_(True),
        )
        .order_by(TradingSystemRuleBinding.sort_order.asc(), TradingSystemRuleBinding.binding_id.asc())
        .all()
    )
    results = []
    for binding, rule in bindings:
        executor = get_executor(rule.executor_key) if rule.executor_key in SAFE_RULE_EXECUTORS else None
        result = None
        reason = "safe executor is not registered; skipped preview"
        if executor is not None:
            context = RuleContext(
                watch_id=watch.id,
                stock_code=watch.stock_code,
                stock_name=watch.stock_name,
                trading_system_code=watch.trading_system_code,
                stage=watch.system_stage or "observe",
                system_params=watch.system_params_json or {},
                rule_config=_rule_config(binding, rule),
                trade_date=trade_date,
                latest_price=quote.latest_price if quote else None,
            )
            result = executor.execute(context)
            reason = result.reason
        results.append(
            {
                "rule_code": rule.rule_code,
                "rule_name": rule.rule_name,
                "rule_display_name": rule.rule_name or rule.rule_code,
                "rule_type": rule.rule_type,
                "timeframe": rule.timeframe,
                "executor_key": rule.executor_key,
                "required": binding.required,
                "logic_group": binding.logic_group,
                "logic_operator": binding.logic_operator,
                "triggered": bool(result.triggered) if result else False,
                "trigger_price": result.trigger_price if result else None,
                "reason": reason,
                "snapshot": _simplify_snapshot(result.snapshot if result else {}),
            }
        )

    required_passed = all(item["triggered"] for item in results if item["required"])
    buy_signal_triggered = any(item["triggered"] for item in results if item["rule_type"] == "buy_signal")
    return {
        "watch_id": watch.id,
        "stock_code": watch.stock_code,
        "stock_name": watch.stock_name,
        "trading_system_code": watch.trading_system_code,
        "system_stage": watch.system_stage or "observe",
        "required_passed": required_passed,
        "buy_signal_triggered": buy_signal_triggered,
        "would_generate_signal": required_passed and buy_signal_triggered,
        "rules": results,
    }


def _trading_system_dict(row: TradingSystemDefinition) -> dict:
    return {
        "system_id": row.system_id,
        "system_code": row.system_code,
        "system_name": row.system_name,
        "description": row.description,
        "lifecycle_desc": row.lifecycle_desc,
        "enabled": row.enabled,
        "sort_order": row.sort_order,
    }


def _trading_param_dict(row: TradingSystemParamDefinition) -> dict:
    return {
        "param_id": row.param_id,
        "system_code": row.system_code,
        "param_key": row.param_key,
        "param_name": row.param_name,
        "param_type": row.param_type,
        "required": row.required,
        "default_value": row.default_value,
        "description": row.description,
        "sort_order": row.sort_order,
        "enabled": row.enabled,
    }


def _signal_dict(
    row: WatchSignal,
    quote: MktStockQuote | None = None,
    rule: TradingRuleDefinition | None = None,
    trading_system_name: str | None = None,
) -> dict:
    rule_code = row.rule_code or row.buy_point_type
    rule_name = rule.rule_name if rule else rule_code
    rule_timeframe = rule.timeframe if rule else row.kline_period
    data = {
        "signal_id": row.signal_id,
        "watch_id": row.watch_id,
        "stock_code": row.stock_code,
        "stock_name": row.stock_name,
        "signal_type": row.signal_type,
        "buy_point_type": row.buy_point_type,
        "trading_system_code": row.trading_system_code,
        "rule_code": row.rule_code,
        "rule_name": rule_name,
        "rule_timeframe": rule_timeframe,
        "rule_display_name": rule_name or rule_code,
        "rule_type": row.rule_type,
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
        "trading_system": row.trading_system,
        "trading_system_name": trading_system_name or row.trading_system_code or row.trading_system,
        "buy_point_confirmed": row.buy_point_confirmed,
        "buy_point_confirm_time": row.buy_point_confirm_time,
        "buy_point_confirm_price": row.buy_point_confirm_price,
        "abandoned_flag": row.abandoned_flag,
        "abandoned_reason": row.abandoned_reason,
        "abandoned_time": row.abandoned_time,
        "prevent_duplicate_signal": row.prevent_duplicate_signal,
        "trigger_signature": row.trigger_signature,
        "snapshot_json": row.snapshot_json or row.raw_snapshot or {},
        "notification_sent": row.notification_sent,
        "notification_sent_at": row.notification_sent_at,
        "notification_error": row.notification_error,
        "assistant_note": ASSISTANT_NOTE,
    }
    data.update(_quote_payload(quote))
    return data


def _trade_dict(
    row: WatchTrade,
    quote: MktStockQuote | None = None,
    rule_map: dict[str, TradingRuleDefinition] | None = None,
    trading_system_name: str | None = None,
) -> dict:
    rule_map = rule_map or {}
    entry_rule = rule_map.get(row.entry_rule_code or "")
    data = {
        "trade_id": row.id,
        "signal_id": row.signal_id,
        "watch_id": row.watch_id,
        "stock_code": row.stock_code,
        "stock_name": row.stock_name,
        "trade_source": row.trade_source,
        "trading_system": row.trading_system,
        "trading_system_code": row.trading_system_code,
        "trading_system_name": trading_system_name or row.trading_system_code or row.trading_system,
        "entry_rule_code": row.entry_rule_code,
        "entry_rule_name": entry_rule.rule_name if entry_rule else row.entry_rule_code,
        "entry_rule_display_name": entry_rule.rule_name if entry_rule else row.entry_rule_code,
        "system_params_json": row.system_params_json or {},
        "active_sell_rule_codes_json": row.active_sell_rule_codes_json or [],
        "active_stop_rule_codes_json": row.active_stop_rule_codes_json or [],
        "active_sell_rules": _rule_payloads(row.active_sell_rule_codes_json or [], rule_map),
        "active_stop_rules": _rule_payloads(row.active_stop_rule_codes_json or [], rule_map),
        "current_stage": row.current_stage or "trading",
        "latest_trade_signal_id": row.latest_trade_signal_id,
        "buy_reason": row.buy_reason,
        "trade_plan": row.trade_plan,
        "emotion_state": row.emotion_state,
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
    data.update(_quote_payload(quote))
    return data


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


TASK_LABELS = {
    "collect_market_daily": "大盘数据采集",
    "collect_hot_sector_rank": "热门板块采集",
    "collect_hot_stock_rank": "热门个股采集",
    "collect_limit_up_daily": "涨停数据采集",
    "update_watch_daily_kline": "自选日 K 更新",
    "update_watch_15m_kline": "自选 15 分钟 K 更新",
    "prepare_watch_kline_data": "观察规则 K 线准备",
    "prepare_trade_kline_data": "交易规则 K 线准备",
    "update_watch_prices": "自选价格更新",
    "scan_watch_signals": "观察信号扫描",
    "scan_watch_rules": "观察规则扫描",
    "scan_watch_remove_rules": "趋势规则自动剔除",
    "scan_trade_rules": "交易规则扫描",
    "auto_remove_watch_pool": "自动剔除",
    "scan_trade_risk_signals": "持仓风险扫描",
    "generate_weekly_review_form": "周复盘生成",
    "generate_monthly_review_form": "月复盘生成",
    "remind_pending_review_form": "复盘提醒",
    "aggregate_review_metrics": "复盘指标汇总",
}

TASK_EXECUTION_PLANS = {
    "collect_market_daily": "每日18点",
    "collect_hot_sector_rank": "每日18点",
    "collect_hot_stock_rank": "每日18点",
    "collect_limit_up_daily": "每日18点",
    "update_watch_prices": "每5分钟",
    "prepare_watch_kline_data": "每5分钟",
    "prepare_trade_kline_data": "每5分钟",
    "scan_watch_signals": "每15分钟",
    "scan_watch_rules": "每15分钟",
    "scan_watch_remove_rules": "每日20点",
    "scan_trade_rules": "每10分钟",
    "auto_remove_watch_pool": "每15分钟",
}

MODULE_LABELS = {
    "market": "数据采集",
    "kline": "K 线更新",
    "signal": "自选监控",
    "review": "复盘任务",
}


def _task_log_dict(row: ConfigTaskLog | None) -> dict | None:
    if not row:
        return None
    return {
        "log_id": row.log_id,
        "task_id": row.task_id,
        "task_name": row.task_name,
        "run_status": row.run_status,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "affected_rows": row.affected_rows,
        "error_message": row.error_message,
    }


def _task_dict(row: ConfigTask, latest_log: ConfigTaskLog | None = None) -> dict:
    execution_plan = TASK_EXECUTION_PLANS.get(row.task_name) or row.cron_expression or "手动执行"
    return {
        "task_id": row.task_id,
        "task_name": row.task_name,
        "task_label": TASK_LABELS.get(row.task_name, row.task_name),
        "execution_plan": execution_plan,
        "task_type": row.task_type,
        "owner_module": row.owner_module,
        "owner_label": MODULE_LABELS.get(row.owner_module, row.owner_module or "其他任务"),
        "cron_expression": row.cron_expression,
        "enabled": row.enabled,
        "running": row.running,
        "retry_times": row.retry_times,
        "timeout_seconds": row.timeout_seconds,
        "latest_log": _task_log_dict(latest_log),
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
def hot_stocks(trade_date: date | None = None, page_no: int = 1, page_size: int = 20, db: Session = Depends(get_db), user=Depends(require_login)):
    rows = PrdMarketDataService(db).get_hot_stocks(trade_date)
    return ok(page(rows[(page_no - 1) * page_size : page_no * page_size], page_no, page_size, len(rows)))


@router.get("/market/limit-ups")
def limit_ups(trade_date: date | None = None, platform: str | None = None, page_no: int = 1, page_size: int = 20, db: Session = Depends(get_db), user=Depends(require_login)):
    service = PrdMarketDataService(db)
    rows = service.get_limit_ups(trade_date, platform)
    payload = page(rows[(page_no - 1) * page_size : page_no * page_size], page_no, page_size, len(rows))
    if trade_date:
        payload["limit_up_ladder"] = service.get_limit_up_ladder(trade_date)
    return ok(payload)


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
        "amount": r.amount,
        "ma5": r.ma5,
        "ma10": r.ma10,
        "ma20": r.ma20,
        "source": r.source,
    } for r in rows])


@router.get("/trading-systems")
def list_trading_systems(db: Session = Depends(get_db), user=Depends(require_login)):
    SeedService(db).init_defaults()
    rows = (
        db.query(TradingSystemDefinition)
        .filter(TradingSystemDefinition.enabled.is_(True))
        .order_by(TradingSystemDefinition.sort_order.asc(), TradingSystemDefinition.system_id.asc())
        .all()
    )
    return ok([_trading_system_dict(row) for row in rows])


@router.get("/trading-systems/{system_code}/params")
def list_trading_system_params(system_code: str, db: Session = Depends(get_db), user=Depends(require_login)):
    SeedService(db).init_defaults()
    rows = (
        db.query(TradingSystemParamDefinition)
        .filter(
            TradingSystemParamDefinition.system_code == system_code,
            TradingSystemParamDefinition.enabled.is_(True),
        )
        .order_by(TradingSystemParamDefinition.sort_order.asc(), TradingSystemParamDefinition.param_id.asc())
        .all()
    )
    return ok([_trading_param_dict(row) for row in rows])


@router.get("/watch-pool")
def list_watch_pool(
    status: str | None = None,
    trading_system: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    query = db.query(WatchPool)
    if status:
        query = query.filter(WatchPool.status == status)
    else:
        query = query.filter(WatchPool.active.is_(True))
    if trading_system:
        query = query.filter(or_(WatchPool.trading_system == trading_system, WatchPool.trading_system_code == trading_system))
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(or_(WatchPool.stock_code.ilike(like), WatchPool.stock_name.ilike(like), WatchPool.entry_reason.ilike(like)))
    rows = query.order_by(WatchPool.created_at.desc()).all()
    quotes = _quote_map(db, [row.stock_code for row in rows])
    names = _system_name_map(db, [row.trading_system_code or row.trading_system for row in rows])
    return ok([_watch_dict(row, quotes.get(row.stock_code), names.get(row.trading_system_code or row.trading_system)) for row in rows])


@router.get("/watch-pool/summary")
def watch_summary(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(PrdWatchPoolService(db).summary())


@router.get("/watch-pool/{watch_id}")
def get_watch(watch_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = PrdWatchPoolService(db).get_watch(watch_id)
    names = _system_name_map(db, [row.trading_system_code or row.trading_system])
    return ok(_watch_dict(row, _quote_map(db, [row.stock_code]).get(row.stock_code), names.get(row.trading_system_code or row.trading_system)))


@router.post("/watch-pool")
def add_watch(payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    try:
        row = PrdWatchPoolService(db).add_watch(payload)
        names = _system_name_map(db, [row.trading_system_code or row.trading_system])
        return ok(_watch_dict(row, _quote_map(db, [row.stock_code]).get(row.stock_code), names.get(row.trading_system_code or row.trading_system)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/watch-pool/{watch_id}")
def update_watch(watch_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    if not payload.get("adjust_reason"):
        raise HTTPException(status_code=400, detail="adjust_reason is required")
    try:
        row = PrdWatchPoolService(db).update_watch(watch_id, payload)
        names = _system_name_map(db, [row.trading_system_code or row.trading_system])
        return ok(_watch_dict(row, _quote_map(db, [row.stock_code]).get(row.stock_code), names.get(row.trading_system_code or row.trading_system)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/watch-pool/{watch_id}/rule-preview")
def preview_watch_rules(watch_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    watch = PrdWatchPoolService(db).get_watch(watch_id)
    return ok(_evaluate_observe_rules(db, watch, date.today()))


@router.post("/watch-pool/{watch_id}/invalid")
def mark_watch_invalid(watch_id: int, payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    try:
        return ok(_watch_dict(PrdWatchPoolService(db).mark_invalid(watch_id, payload)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/watch-pool/{watch_id}")
def remove_watch(watch_id: int, remove_reason: str = "用户剔除", db: Session = Depends(get_db), user=Depends(require_login)):
    return ok(_watch_dict(PrdWatchPoolService(db).remove_watch(watch_id, remove_reason)))


@router.delete("/watch-pool/{watch_id}/hard-delete")
def hard_delete_watch(watch_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    try:
        return ok(PrdWatchPoolService(db).hard_delete_watch(watch_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


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
            "operation_type": row.operation_type,
            "snapshot": row.snapshot,
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
    quotes = _quote_map(db, [row.stock_code for row in rows])
    rules = _rule_map(db, [row.rule_code or row.buy_point_type for row in rows])
    systems = _system_name_map(db, [row.trading_system_code or row.trading_system for row in rows])
    return ok([
        _signal_dict(row, quotes.get(row.stock_code), rules.get(row.rule_code or row.buy_point_type), systems.get(row.trading_system_code or row.trading_system))
        for row in rows
    ])


@router.get("/watch-signals/recent")
def recent_watch_signals(limit: int = 10, db: Session = Depends(get_db), user=Depends(require_login)):
    rows = db.query(WatchSignal).order_by(WatchSignal.trigger_time.desc()).limit(min(limit, 50)).all()
    quotes = _quote_map(db, [row.stock_code for row in rows])
    rules = _rule_map(db, [row.rule_code or row.buy_point_type for row in rows])
    systems = _system_name_map(db, [row.trading_system_code or row.trading_system for row in rows])
    return ok([
        _signal_dict(row, quotes.get(row.stock_code), rules.get(row.rule_code or row.buy_point_type), systems.get(row.trading_system_code or row.trading_system))
        for row in rows
    ])


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
    rule_code = row.rule_code or row.buy_point_type
    return ok(_signal_dict(
        row,
        _quote_map(db, [row.stock_code]).get(row.stock_code),
        _rule_map(db, [rule_code]).get(rule_code),
        _system_name_map(db, [row.trading_system_code or row.trading_system]).get(row.trading_system_code or row.trading_system),
    ))


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


@router.post("/watch-signals/{signal_id}/abandon")
def abandon_signal(signal_id: int, payload: dict | None = None, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(WatchSignal).filter(WatchSignal.signal_id == signal_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="signal not found")
    reason = (payload or {}).get("reason") or (payload or {}).get("abandoned_reason") or "user abandoned signal"
    row.abandoned_flag = True
    row.abandoned_reason = reason
    row.abandoned_time = datetime.utcnow()
    row.signal_status = "abandoned"
    row.user_action = "abandoned"
    row.handled_at = row.abandoned_time
    row.raw_snapshot = {**(row.raw_snapshot or {}), "abandon_reason": reason}
    if row.watch_id:
        watch = db.query(WatchPool).filter(WatchPool.id == row.watch_id).first()
        if watch:
            old_status = watch.status or watch.status
            watch.status = "watching"
            watch.system_stage = "observe"
            watch.monitor_enabled = True
            watch.signal_enabled = True
            watch.next_action = "等待下一次买点"
            db.add(
                WatchPoolStatusLog(
                    watch_id=watch.id,
                    stock_code=watch.stock_code,
                    from_status=old_status,
                    to_status="watching",
                    change_reason=reason,
                    operator_type="user",
                    operation_type="abandon_signal",
                    snapshot={"signal_id": signal_id, "reason": reason},
                )
            )
    db.commit()
    db.refresh(row)
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
    from app.services.trade_context import apply_confirm_buy_trade_context

    signal = db.query(WatchSignal).filter(WatchSignal.signal_id == signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="signal not found")
    existing_by_signal = db.query(WatchTrade).filter(WatchTrade.signal_id == signal_id).first()
    if existing_by_signal:
        watch = db.query(WatchPool).filter(WatchPool.id == signal.watch_id).first() if signal.watch_id else None
        apply_confirm_buy_trade_context(db, existing_by_signal, signal, watch)
        db.commit()
        return ok(_trade_dict(existing_by_signal), message="signal already confirmed")
    if signal.signal_status != "buy_pending_confirm":
        raise HTTPException(status_code=400, detail="signal_status must be buy_pending_confirm")
    if payload.get("buy_point_confirmed") is not True:
        raise HTTPException(status_code=400, detail="buy_point_confirmed is required")
    if payload.get("stop_loss_price") in (None, ""):
        raise HTTPException(status_code=400, detail="stop_loss_price is required")
    buy_price = float(payload["buy_price"])
    amount = float(payload["amount"])
    watch = db.query(WatchPool).filter(WatchPool.id == signal.watch_id).first() if signal.watch_id else None
    trade = (
        db.query(WatchTrade)
        .filter(WatchTrade.stock_code == signal.stock_code, WatchTrade.trade_status.in_(["open", "holding"]))
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
            trading_system=signal.trading_system,
            trading_system_code=signal.trading_system_code or (watch.trading_system_code if watch else None),
            entry_rule_code=signal.rule_code or signal.buy_point_type,
            first_buy_time=now,
            first_buy_price=buy_price,
            total_buy_amount=amount,
            remaining_amount=amount,
            average_buy_price=buy_price,
            position_ratio=payload.get("position_ratio"),
            stop_loss_price=payload.get("stop_loss_price"),
            target_price=payload.get("target_price"),
            trade_status="open",
            buy_reason=payload.get("buy_reason", signal.trigger_reason or ""),
            trade_plan=payload.get("trade_plan", ""),
            emotion_state=payload.get("emotion_state"),
            remark=payload.get("remark", ""),
        )
        db.add(trade)
        db.flush()
    else:
        total_cost = (trade.average_buy_price or 0) * trade.total_buy_amount + buy_price * amount
        trade.total_buy_amount += amount
        trade.remaining_amount += amount
        trade.average_buy_price = total_cost / trade.total_buy_amount if trade.total_buy_amount else buy_price
    apply_confirm_buy_trade_context(db, trade, signal, watch)
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
    signal.buy_point_confirmed = True
    signal.buy_point_confirm_time = now
    signal.buy_point_confirm_price = buy_price
    if signal.watch_id:
        if watch:
            old_status = watch.status or watch.status
            watch.status = "trading"
            watch.system_stage = "trading"
            watch.monitor_enabled = False
            watch.signal_enabled = False
            db.add(
                WatchPoolStatusLog(
                    watch_id=watch.id,
                    stock_code=watch.stock_code,
                    from_status=old_status,
                    to_status="trading",
                    change_reason="user confirmed buy",
                    operator_type="user",
                    operation_type="confirm_buy",
                    snapshot={"signal_id": signal_id, "trade_id": trade.id, "buy_price": buy_price, "amount": amount},
                )
            )
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
    rows = query.order_by(WatchTrade.created_at.desc()).limit(100).all()
    quotes = _quote_map(db, [row.stock_code for row in rows])
    rule_codes = []
    for row in rows:
        rule_codes.extend([row.entry_rule_code, *(row.active_sell_rule_codes_json or []), *(row.active_stop_rule_codes_json or [])])
    rules = _rule_map(db, rule_codes)
    systems = _system_name_map(db, [row.trading_system_code or row.trading_system for row in rows])
    return ok([
        _trade_dict(row, quotes.get(row.stock_code), rules, systems.get(row.trading_system_code or row.trading_system))
        for row in rows
    ])


@router.get("/watch-trades/recent")
def recent_watch_trades(limit: int = 10, db: Session = Depends(get_db), user=Depends(require_login)):
    rows = db.query(WatchTrade).order_by(WatchTrade.created_at.desc()).limit(min(limit, 50)).all()
    quotes = _quote_map(db, [row.stock_code for row in rows])
    rule_codes = []
    for row in rows:
        rule_codes.extend([row.entry_rule_code, *(row.active_sell_rule_codes_json or []), *(row.active_stop_rule_codes_json or [])])
    rules = _rule_map(db, rule_codes)
    systems = _system_name_map(db, [row.trading_system_code or row.trading_system for row in rows])
    return ok([
        _trade_dict(row, quotes.get(row.stock_code), rules, systems.get(row.trading_system_code or row.trading_system))
        for row in rows
    ])


@router.get("/watch-trades/summary")
def watch_trade_summary(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok({
        "total": db.query(WatchTrade).count(),
        "open": db.query(WatchTrade).filter(WatchTrade.trade_status.in_(["open", "holding"])).count(),
        "completed": db.query(WatchTrade).filter(WatchTrade.trade_status == "completed").count(),
    })


@router.get("/watch-trades/{trade_id}")
def get_watch_trade(trade_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(WatchTrade).filter(WatchTrade.id == trade_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="trade not found")
    rule_codes = [row.entry_rule_code, *(row.active_sell_rule_codes_json or []), *(row.active_stop_rule_codes_json or [])]
    return ok(_trade_dict(
        row,
        _quote_map(db, [row.stock_code]).get(row.stock_code),
        _rule_map(db, rule_codes),
        _system_name_map(db, [row.trading_system_code or row.trading_system]).get(row.trading_system_code or row.trading_system),
    ))


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
    remaining = float(trade.remaining_amount or 0)
    if payload.get("is_full_exit") is not True or abs(amount - remaining) > 0.000001:
        raise HTTPException(status_code=400, detail="BAD_REQUEST: MVP only supports full exit")
    execution_type = payload.get("execution_type", "sell")
    execution_time = datetime.fromisoformat(payload["execution_time"]) if payload.get("execution_time") else datetime.utcnow()
    duplicate = (
        db.query(WatchTradeExecution)
        .filter(WatchTradeExecution.trade_id == trade_id, WatchTradeExecution.execution_time == execution_time, WatchTradeExecution.execution_type == execution_type)
        .first()
    )
    if duplicate:
        return ok(_execution_dict(duplicate), message="duplicate execution ignored")
    buy_price = trade.average_buy_price or trade.first_buy_price or sell_price
    pnl_amount = (sell_price - buy_price) * amount
    pnl_ratio = (sell_price - buy_price) / buy_price if buy_price else 0.0
    is_full_exit = True
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
    trade.remaining_amount = 0
    trade.trade_status = "completed"
    trade.closed_at = execution_time
    if not db.query(ReviewTrade).filter(ReviewTrade.trade_id == trade.id).first():
        db.add(ReviewTrade(trade_id=trade.id, final_pnl_ratio=trade.pnl_ratio, status="pending"))
    if trade.watch_id:
        watch = db.query(WatchPool).filter(WatchPool.id == trade.watch_id).first()
        if watch:
            old_status = watch.status or watch.status
            watch.status = "pending_review"
            watch.status = "pending_review"
            watch.monitor_enabled = False
            watch.signal_enabled = False
            db.add(
                WatchPoolStatusLog(
                    watch_id=watch.id,
                    stock_code=watch.stock_code,
                    from_status=old_status,
                    to_status="pending_review",
                    change_reason=payload.get("execution_reason", "user confirmed full sell"),
                    operator_type="user",
                    operation_type="confirm_sell",
                    snapshot={"trade_id": trade.id, "sell_price": sell_price, "amount": amount, "pnl_ratio": trade.pnl_ratio},
                )
            )
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
    rows = db.query(ReviewForm).filter(ReviewForm.status.in_(["pending", "editing"])).all()
    return ok([_review_dict(row) for row in rows])


@router.get("/reviews/summary")
def review_summary(db: Session = Depends(get_db), user=Depends(require_login)):
    return ok({
        "total": db.query(ReviewForm).count(),
        "pending": db.query(ReviewForm).filter(ReviewForm.status == "pending").count(),
        "completed": db.query(ReviewForm).filter(ReviewForm.status == "completed").count(),
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


@router.get("/me/notification-email")
def notification_email(db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(MyUserPreference).filter_by(preference_type="notification", preference_key="email").first()
    return ok({"email": row.preference_value.get("address", "") if row else ""})


@router.put("/me/notification-email")
def save_notification_email(payload: dict, db: Session = Depends(get_db), user=Depends(require_login)):
    row = db.query(MyUserPreference).filter_by(preference_type="notification", preference_key="email").first()
    if not row:
        row = MyUserPreference(preference_type="notification", preference_key="email")
        db.add(row)
    row.preference_value = {"address": payload.get("email", "").strip()}
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


@router.get("/me/tasks")
def my_tasks(db: Session = Depends(get_db), user=Depends(require_login)):
    SeedService(db).init_defaults()
    tasks = db.query(ConfigTask).order_by(ConfigTask.owner_module, ConfigTask.task_id).all()
    latest_logs: dict[str, ConfigTaskLog] = {}
    for log in db.query(ConfigTaskLog).order_by(ConfigTaskLog.started_at.desc()).limit(300).all():
        latest_logs.setdefault(log.task_name, log)
    rows = [_task_dict(task, latest_logs.get(task.task_name)) for task in tasks]
    failed = sum(1 for item in rows if item["latest_log"] and item["latest_log"]["run_status"] == "failed")
    running = sum(1 for item in rows if item["running"])
    enabled = sum(1 for item in rows if item["enabled"])
    return ok({
        "summary": {
            "total": len(rows),
            "enabled": enabled,
            "running": running,
            "failed": failed,
        },
        "groups": [
            {"module": module, "label": label, "tasks": [item for item in rows if item["owner_module"] == module]}
            for module, label in MODULE_LABELS.items()
            if any(item["owner_module"] == module for item in rows)
        ],
        "tasks": rows,
    })


@router.get("/me/task-logs")
def my_task_logs(limit: int = 50, db: Session = Depends(get_db), user=Depends(require_login)):
    rows = db.query(ConfigTaskLog).order_by(ConfigTaskLog.started_at.desc()).limit(min(max(limit, 1), 100)).all()
    return ok([_task_log_dict(row) for row in rows])


@router.post("/me/tasks/{task_id}/run")
def run_my_task(task_id: int, db: Session = Depends(get_db), user=Depends(require_login)):
    from app.services.tasks import TaskService

    SeedService(db).init_defaults()
    task = db.query(ConfigTask).filter(ConfigTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    if task.running:
        raise HTTPException(status_code=409, detail="task is running")
    svc = TaskService(db)
    fn_map = {
        "collect_market_daily": svc.collect_market_daily,
        "collect_hot_sector_rank": svc.collect_hot_sector_rank,
        "collect_hot_stock_rank": svc.collect_hot_stock_rank,
        "collect_limit_up_daily": svc.collect_limit_up_daily,
        "update_watch_daily_kline": svc.update_watch_daily_kline,
        "update_watch_15m_kline": svc.update_watch_15m_kline,
        "prepare_watch_kline_data": svc.prepare_watch_kline_data,
        "prepare_trade_kline_data": svc.prepare_trade_kline_data,
        "update_watch_prices": svc.update_watch_prices,
        "scan_watch_signals": svc.scan_watch_signals,
        "scan_watch_rules": svc.scan_watch_rules,
        "scan_watch_remove_rules": svc.scan_watch_remove_rules,
        "scan_trade_rules": svc.scan_trade_rules,
        "auto_remove_watch_pool": svc.auto_remove_watch_pool,
        "scan_trade_risk_signals": svc.scan_trade_risk_signals,
        "generate_weekly_review_form": svc.generate_weekly_review_form,
        "generate_monthly_review_form": svc.generate_monthly_review_form,
        "remind_pending_review_form": svc.remind_pending_review_form,
        "aggregate_review_metrics": svc.aggregate_review_metrics,
    }
    fn = fn_map.get(task.task_name)
    if not fn:
        raise HTTPException(status_code=400, detail=f"unsupported task: {task.task_name}")
    log = fn(date.today())
    return ok({
        "task": _task_dict(task, log),
        "log": _task_log_dict(log),
    })


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
