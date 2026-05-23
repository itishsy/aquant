from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import TradingRuleDefinition, TradingSystemRuleBinding, WatchPool, WatchSignal, WatchTrade


def _enabled_rule_codes(db: Session, system_code: str | None, stages: set[str]) -> list[str]:
    if not system_code:
        return []
    rows = (
        db.query(TradingSystemRuleBinding.rule_code)
        .join(TradingRuleDefinition, TradingRuleDefinition.rule_code == TradingSystemRuleBinding.rule_code)
        .filter(
            TradingSystemRuleBinding.system_code == system_code,
            TradingSystemRuleBinding.stage.in_(stages),
            TradingSystemRuleBinding.enabled.is_(True),
            TradingRuleDefinition.enabled.is_(True),
        )
        .order_by(TradingSystemRuleBinding.stage.asc(), TradingSystemRuleBinding.sort_order.asc())
        .all()
    )
    return [row[0] for row in rows]


def apply_confirm_buy_trade_context(
    db: Session,
    trade: WatchTrade,
    signal: WatchSignal,
    watch: WatchPool | None,
) -> None:
    system_code = signal.trading_system_code or (watch.trading_system_code if watch else None) or signal.trading_system
    trade.trading_system_code = system_code
    trade.trading_system = trade.trading_system or system_code or signal.trading_system
    trade.entry_rule_code = signal.rule_code or signal.buy_point_type
    trade.system_params_json = dict(watch.system_params_json or {}) if watch else dict(trade.system_params_json or {})
    trade.active_sell_rule_codes_json = _enabled_rule_codes(db, system_code, {"trading", "sell"})
    trade.active_stop_rule_codes_json = _enabled_rule_codes(db, system_code, {"stop_loss"})
    trade.current_stage = "trading"
    trade.latest_trade_signal_id = signal.signal_id
