from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import (
    ConfigDictionary,
    ConfigNotificationTemplate,
    ConfigOperationLog,
    ConfigReviewTemplate,
    ConfigStrategy,
    ConfigTask,
    MktDaily,
    MktDailyPlate,
    MktDailyPlateStock,
    MktDailyTopic,
    MktDailyTopicStock,
    MktHotStock,
    MktLimitUpStock,
    MyNotificationSetting,
    MyUserProfile,
    WatchPool,
    WatchPoolStatusLog,
    WatchSignal,
    WatchSignalPerformance,
    WatchTrade,
    WatchTradeExecution,
    ReviewTrade,
    TradingRuleDefinition,
    TradingSystemDefinition,
    TradingSystemParamDefinition,
    TradingSystemRuleBinding,
)
from app.services.normalization import normalize_stock_code, xueqiu_link


ASSISTANT_NOTE = "仅作为交易辅助，请结合个人交易规则确认。"


class SeedService:
    DICTS = {
        "watch_tag": [("popularity", "人气"), ("relay", "接力"), ("trend", "趋势")],
        "operation_strategy": [("trend_trade", "趋势交易"), ("accelerated_relay", "加速接力"), ("platform_breakout", "平台突破")],
        "buy_point_type": [
            ("b15_divergence", "B15 底背离买点"),
            ("support_buy", "支撑买点"),
            ("platform_breakout_confirm", "平台突破确认买点"),
        ],
        "trading_system": [
            ("platform_breakout", "平台突破"),
            ("uptrend", "上涨趋势"),
            ("relay", "追涨接力"),
        ],
        "watch_lifecycle_status": [
            ("watching", "观察中"),
            ("signal_generated", "买入信号已生成"),
            ("waiting_buy_point", "等待买点确认"),
            ("buy_pending_confirm", "买入待确认"),
            ("trading", "交易中"),
            ("sell_signal_pending", "卖出信号待处理"),
            ("sell_delayed", "卖出延后处理"),
            ("sold", "已卖出"),
            ("pending_review", "待复盘"),
            ("archived", "已归档"),
            ("invalid", "已失效"),
            ("blacklist", "黑名单"),
            ("removed", "已剔除"),
        ],
        "watch_invalid_reason": [
            ("market_weak", "市场转弱"),
            ("sector_weak", "板块转弱"),
            ("technical_invalid", "技术形态失效"),
            ("break_key_price", "跌破关键价"),
            ("risk_high", "风险过高"),
            ("user_cancel", "用户不再关注"),
        ],
        "signal_abandon_reason": [
            ("unclear_buy_point", "买点不清晰"),
            ("bad_risk_reward", "风险收益比不合适"),
            ("market_weak", "市场转弱"),
            ("sector_weak", "板块转弱"),
            ("price_deviation", "价格偏离买点"),
            ("user_skip", "用户放弃本次机会"),
        ],
        "sell_reason": [
            ("stop_loss", "止损"),
            ("take_profit", "止盈"),
            ("system_rule_break", "跌破体系规则"),
            ("breakout_failure", "突破失败"),
            ("trend_broken", "趋势破坏"),
            ("relay_failed", "接力失败"),
            ("high_volume_risk", "高位放量风险"),
            ("weak_seal", "封板弱"),
            ("manual_sell", "手动卖出"),
        ],
        "emotion_state": [("calm", "冷静"), ("hesitant", "犹豫"), ("impulsive", "冲动"), ("fearful", "害怕踏空")],
        "risk_tag": [
            ("high_position", "高位"),
            ("weak_seal", "封板弱"),
            ("shrinking_volume", "缩量"),
            ("sector_weak", "板块转弱"),
            ("abnormal_volume", "放量异常"),
            ("break_support", "跌破支撑"),
        ],
        "signal_status": [("pending", "未处理"), ("confirmed_buy", "已确认买入"), ("ignored", "已忽略"), ("invalid", "已失效")],
        "signal_user_action": [("pending", "未处理"), ("confirmed_buy", "已确认买入"), ("ignored", "已忽略"), ("false_positive", "标记误报")],
        "trade_status": [("open", "持仓中"), ("completed", "已完成"), ("cancelled", "已取消"), ("invalid", "已失效")],
        "review_status": [("pending", "待填写"), ("editing", "填写中"), ("completed", "已完成"), ("archived", "已归档")],
        "issue_tag": [
            ("chase_high", "追高买入"),
            ("stop_loss_hesitation", "止损犹豫"),
            ("late_take_profit", "止盈不及时"),
            ("heavy_position", "仓位过重"),
            ("emotional_trade", "情绪化交易"),
            ("non_signal_trade", "非信号交易"),
        ],
        "attribution_type": [
            ("market", "市场问题"),
            ("sector", "板块问题"),
            ("stock", "个股问题"),
            ("buy_point", "买点问题"),
            ("sell_point", "卖点问题"),
            ("position", "仓位问题"),
            ("discipline", "纪律问题"),
            ("emotion", "情绪问题"),
            ("strategy", "策略问题"),
            ("data", "数据问题"),
        ],
    }

    TASKS = [
        ("collect_market_daily", "market"),
        ("collect_hot_sector_rank", "market"),
        ("collect_hot_stock_rank", "market"),
        ("collect_limit_up_daily", "market"),
        ("update_watch_daily_kline", "market"),
        ("update_watch_15m_kline", "market"),
        ("prepare_watch_kline_data", "kline"),
        ("prepare_trade_kline_data", "kline"),
        ("update_watch_prices", "signal"),
        ("scan_watch_signals", "signal"),
        ("scan_watch_rules", "signal"),
        ("scan_trade_rules", "signal"),
        ("auto_remove_watch_pool", "signal"),
        ("scan_trade_risk_signals", "signal"),
        ("generate_weekly_review_form", "review"),
        ("generate_monthly_review_form", "review"),
        ("remind_pending_review_form", "review"),
        ("aggregate_review_metrics", "review"),
    ]
    TEMPLATES = ["买入观察信号", "卖出提醒", "风险提醒", "复盘提醒", "任务异常提醒"]

    TRADING_SYSTEMS = [
        ("platform_breakout", "平台突破", "以平台整理后的突破、回踩和失效条件为核心的交易体系样板。", "观察 -> 买点确认 -> 交易中 -> 卖出/止损 -> 复盘", 1),
        ("uptrend", "上涨趋势", "用于承载趋势跟随类交易规则的体系定义。", "观察 -> 趋势确认 -> 交易中 -> 卖出/止损 -> 复盘", 2),
        ("limit_relay", "涨停接力", "用于承载涨停接力类交易规则的体系定义。", "观察 -> 接力确认 -> 交易中 -> 卖出/止损 -> 复盘", 3),
        ("oversold_rebound", "超跌反弹", "用于承载超跌修复类交易规则的体系定义。", "观察 -> 反弹确认 -> 交易中 -> 卖出/止损 -> 复盘", 4),
    ]
    TASK_CONFIG_DEFAULTS = {
        "prepare_watch_kline_data": {
            "interval_minutes": 5,
            "timeframes": ["daily", "5m", "15m", "30m"],
            "max_requests_per_run": 100,
            "source_priority": ["mock"],
        },
        "prepare_trade_kline_data": {
            "interval_minutes": 5,
            "timeframes": ["daily", "5m", "15m", "30m"],
            "max_requests_per_run": 100,
            "source_priority": ["mock"],
        },
        "scan_watch_rules": {"interval_minutes": 10, "quote_max_age_minutes": 10},
        "scan_trade_rules": {"interval_minutes": 10, "quote_max_age_minutes": 10},
    }
    PLATFORM_BREAKOUT_PARAMS = [
        ("platform_upper_price", "箱体上沿", "number", True, None, "平台箱体上沿价格。", 1),
        ("platform_support_price", "平台支撑位", "number", True, None, "平台结构的关键支撑价格。", 2),
        ("key_observe_price", "关键观察价", "number", True, None, "进入观察后的关键跟踪价格。", 3),
        ("auto_remove_price", "自动剔除价", "number", False, None, "跌破后可用于自动剔除观察的价格。", 4),
        ("invalid_condition", "失效条件", "text", True, None, "平台突破体系失效的文字化条件。", 5),
    ]
    PLATFORM_BREAKOUT_RULES = [
        ("not_break_platform_upper", "不跌破箱体上沿", "filter", "daily", "not_break_price", "平台回踩阶段不跌破箱体上沿。"),
        ("b5_divergence", "5分钟底背离", "buy_signal", "5m", "macd_bottom_divergence", "5分钟 MACD 底背离买点信号。"),
        ("b15_divergence", "15分钟底背离", "buy_signal", "15m", "macd_bottom_divergence", "15分钟 MACD 底背离买点信号。"),
        ("m5_top_divergence", "5分钟顶背离", "sell_signal", "5m", "macd_top_divergence", "5分钟 MACD 顶背离卖出信号。"),
        ("m30_dead_cross", "30分钟死叉", "sell_signal", "30m", "macd_dead_cross", "30分钟 MACD 死叉卖出信号。"),
        ("break_platform_support", "收破平台支撑位", "stop_loss", "daily", "break_price", "日线收破平台支撑位止损信号。"),
    ]
    GENERIC_OBSERVE_RULES = [
        ("observe_break_key_price", "观察跌破关键观察价", "observe_risk", "daily", "break_level", "观察阶段跌破关键观察价的风险提醒。"),
        ("observe_close_break_platform_support", "观察收破平台支撑位", "invalid_signal", "daily", "break_level", "观察阶段日线收破平台支撑位的失效提醒。"),
        ("observe_break_ma5", "观察跌破 MA5", "observe_risk", "daily", "break_ma", "观察阶段跌破 MA5 的短线风险提醒。"),
        ("observe_break_ma10", "观察跌破 MA10", "observe_risk", "daily", "break_ma", "观察阶段跌破 MA10 的趋势风险提醒。"),
        ("observe_break_ma20", "观察跌破 MA20", "invalid_signal", "daily", "break_ma", "观察阶段跌破 MA20 的失效提醒。"),
        ("observe_pullback_recent_high", "观察从近期高点回撤", "observe_risk", "daily", "pullback_to_level", "观察阶段从近期高点回撤到指定幅度的提醒。"),
    ]
    PLATFORM_BREAKOUT_RULE_BINDINGS = [
        ("not_break_platform_upper", "observe", True, "platform_retest", "AND", 1),
        ("b5_divergence", "observe", False, "bottom_divergence", "OR", 2),
        ("b15_divergence", "observe", False, "bottom_divergence", "OR", 3),
        ("m5_top_divergence", "trading", False, "sell_signal", "OR", 1),
        ("m30_dead_cross", "trading", False, "sell_signal", "OR", 2),
        ("break_platform_support", "stop_loss", False, "stop_loss", "OR", 1),
    ]
    PLATFORM_BREAKOUT_EXAMPLE_RULE_BINDINGS = [
        ("observe_break_key_price", "observe", False, "observe_risk", "OR", 20, False, {"data": {"timeframe": "daily", "lookback_bars": 5, "indicators": []}, "signal": {"target_param": "key_observe_price", "break_type": "intraday_below", "threshold_pct": 0}}),
        ("observe_close_break_platform_support", "observe", False, "observe_invalid", "OR", 21, False, {"data": {"timeframe": "daily", "lookback_bars": 5, "indicators": []}, "signal": {"target_param": "platform_support_price", "break_type": "close_below", "threshold_pct": 0}}),
        ("observe_break_ma5", "observe", False, "observe_ma", "OR", 22, False, {"data": {"timeframe": "daily", "lookback_bars": 30, "indicators": ["ma"]}, "signal": {"ma": 5, "break_type": "cross_down"}}),
        ("observe_break_ma10", "observe", False, "observe_ma", "OR", 23, False, {"data": {"timeframe": "daily", "lookback_bars": 30, "indicators": ["ma"]}, "signal": {"ma": 10, "break_type": "cross_down"}}),
        ("observe_break_ma20", "observe", False, "observe_ma", "OR", 24, False, {"data": {"timeframe": "daily", "lookback_bars": 30, "indicators": ["ma"]}, "signal": {"ma": 20, "break_type": "cross_down"}}),
        ("observe_pullback_recent_high", "observe", False, "observe_pullback", "OR", 25, False, {"data": {"timeframe": "daily", "lookback_bars": 20, "indicators": []}, "signal": {"mode": "from_recent_high", "pullback_pct": 0.03}}),
    ]

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _dict_items(values: list) -> list[tuple[str, str]]:
        result = []
        for item in values:
            if isinstance(item, tuple):
                result.append((item[0], item[1]))
            else:
                result.append((item, item))
        return result

    def init_defaults(self) -> dict:
        created = 0
        for dict_type, values in self.DICTS.items():
            for order, (code, label) in enumerate(self._dict_items(values), start=1):
                if not self.db.query(ConfigDictionary).filter_by(dict_type=dict_type, dict_value=code).first():
                    self.db.add(
                        ConfigDictionary(
                            dict_type=dict_type,
                            dict_label=label,
                            dict_value=code,
                            sort_order=order,
                        )
                    )
                    created += 1
        for name, owner in self.TASKS:
            task = self.db.query(ConfigTask).filter_by(task_name=name).first()
            default_config = self.TASK_CONFIG_DEFAULTS.get(name, {})
            if not task:
                self.db.add(ConfigTask(task_name=name, task_type="scheduled", owner_module=owner, enabled=True, config_json=default_config))
                created += 1
            elif default_config and not task.config_json:
                task.config_json = default_config
        for code, label in self._dict_items(self.DICTS["buy_point_type"]):
            if not self.db.query(ConfigStrategy).filter_by(strategy_name=label).first():
                self.db.add(
                    ConfigStrategy(
                        strategy_name=label,
                        strategy_type="buy",
                        buy_point_type=code,
                        enabled=True,
                    )
                )
                created += 1
        for name in self.TEMPLATES:
            if not self.db.query(ConfigNotificationTemplate).filter_by(push_type=name, channel="site").first():
                self.db.add(
                    ConfigNotificationTemplate(
                        push_type=name,
                        channel="site",
                        title_template=name,
                        content_template=f"{name}: {{content}}\n{ASSISTANT_NOTE}",
                    )
                )
                created += 1
            if not self.db.query(MyNotificationSetting).filter_by(push_type=name, channel="site").first():
                self.db.add(MyNotificationSetting(push_type=name, channel="site", enabled=True))
                created += 1
        for review_type in ["weekly", "monthly", "trade"]:
            if not self.db.query(ConfigReviewTemplate).filter_by(review_type=review_type).first():
                self.db.add(ConfigReviewTemplate(review_type=review_type, template_name=f"{review_type} 默认模板"))
                created += 1
        if not self.db.query(MyUserProfile).first():
            self.db.add(MyUserProfile(nickname="Aquant User", bio="单用户交易复盘训练系统"))
            created += 1
        created += self._init_trading_system_defaults()
        self.db.commit()
        return {"created": created}

    def _init_trading_system_defaults(self) -> int:
        created = 0
        for code, name, description, lifecycle_desc, sort_order in self.TRADING_SYSTEMS:
            if not self.db.query(TradingSystemDefinition).filter_by(system_code=code).first():
                self.db.add(
                    TradingSystemDefinition(
                        system_code=code,
                        system_name=name,
                        description=description,
                        lifecycle_desc=lifecycle_desc,
                        enabled=True,
                        sort_order=sort_order,
                    )
                )
                created += 1
        for param_key, param_name, param_type, required, default_value, description, sort_order in self.PLATFORM_BREAKOUT_PARAMS:
            if not self.db.query(TradingSystemParamDefinition).filter_by(system_code="platform_breakout", param_key=param_key).first():
                self.db.add(
                    TradingSystemParamDefinition(
                        system_code="platform_breakout",
                        param_key=param_key,
                        param_name=param_name,
                        param_type=param_type,
                        required=required,
                        default_value=default_value,
                        description=description,
                        sort_order=sort_order,
                        enabled=True,
                    )
                )
                created += 1
        for rule_code, rule_name, rule_type, timeframe, executor_key, description in self.PLATFORM_BREAKOUT_RULES:
            if not self.db.query(TradingRuleDefinition).filter_by(rule_code=rule_code).first():
                self.db.add(
                    TradingRuleDefinition(
                        rule_code=rule_code,
                        rule_name=rule_name,
                        rule_type=rule_type,
                        timeframe=timeframe,
                        executor_key=executor_key,
                        description=description,
                        enabled=True,
                    )
                )
                created += 1
        for rule_code, rule_name, rule_type, timeframe, executor_key, description in self.GENERIC_OBSERVE_RULES:
            if not self.db.query(TradingRuleDefinition).filter_by(rule_code=rule_code).first():
                self.db.add(
                    TradingRuleDefinition(
                        rule_code=rule_code,
                        rule_name=rule_name,
                        rule_type=rule_type,
                        timeframe=timeframe,
                        executor_key=executor_key,
                        description=description,
                        enabled=True,
                    )
                )
                created += 1
        for rule_code, stage, required, logic_group, logic_operator, sort_order in self.PLATFORM_BREAKOUT_RULE_BINDINGS:
            if not self.db.query(TradingSystemRuleBinding).filter_by(system_code="platform_breakout", rule_code=rule_code, stage=stage).first():
                self.db.add(
                    TradingSystemRuleBinding(
                        system_code="platform_breakout",
                        rule_code=rule_code,
                        stage=stage,
                        required=required,
                        logic_group=logic_group,
                        logic_operator=logic_operator,
                        sort_order=sort_order,
                        enabled=True,
                        config_json={},
                    )
                )
                created += 1
        for rule_code, stage, required, logic_group, logic_operator, sort_order, enabled, config_json in self.PLATFORM_BREAKOUT_EXAMPLE_RULE_BINDINGS:
            if not self.db.query(TradingSystemRuleBinding).filter_by(system_code="platform_breakout", rule_code=rule_code, stage=stage).first():
                self.db.add(
                    TradingSystemRuleBinding(
                        system_code="platform_breakout",
                        rule_code=rule_code,
                        stage=stage,
                        required=required,
                        logic_group=logic_group,
                        logic_operator=logic_operator,
                        sort_order=sort_order,
                        enabled=enabled,
                        config_json=config_json,
                    )
                )
                created += 1
        return created


class PrdMarketDataService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _hot_stock_code(stock_code: str) -> str:
        text = str(stock_code or "").strip()
        lower = text.lower()
        if lower.startswith(("sh", "sz", "bj")):
            return lower
        normalized = normalize_stock_code(text)
        return f"{normalized[:2].lower()}{normalized[2:]}"

    def _daily_chances(self, trade_date: date) -> list[dict]:
        rows = (
            self.db.query(MktDailyPlate)
            .filter(MktDailyPlate.trade_date == trade_date, MktDailyPlate.plate_type == "chance")
            .order_by(MktDailyPlate.rank_no.asc(), MktDailyPlate.id.asc())
            .all()
        )
        result = []
        for row in rows:
            stocks = (
                self.db.query(MktDailyPlateStock)
                .filter(MktDailyPlateStock.plate_id == row.id)
                .order_by(MktDailyPlateStock.id.asc())
                .all()
            )
            result.append({
                "source": row.platform,
                "kind": "today_chance",
                "subject_id": row.plate_code,
                "subject_name": row.plate_name,
                "title": row.plate_name,
                "description": row.description,
                "jump_url": row.jump_url,
                "rank_no": row.rank_no,
                "article_id": None,
                "article_time": None,
                "attention_num": None,
                "stocks": [
                    {
                        "stock_code": stock.stock_code,
                        "stock_name": stock.stock_name,
                        "change_pct": stock.change_pct,
                        "last_price": stock.last_price,
                    }
                    for stock in stocks
                ],
            })
        return result

    def _daily_tuyeres(self, trade_date: date) -> list[dict]:
        rows = (
            self.db.query(MktDailyPlate)
            .filter(MktDailyPlate.trade_date == trade_date, MktDailyPlate.plate_type == "tuyere")
            .order_by(MktDailyPlate.rank_no.asc(), MktDailyPlate.id.asc())
            .all()
        )
        result = []
        for row in rows:
            stocks = (
                self.db.query(MktDailyPlateStock)
                .filter(MktDailyPlateStock.plate_id == row.id)
                .order_by(MktDailyPlateStock.id.asc())
                .all()
            )
            result.append({
                "source": row.platform,
                "kind": "today_tuyere",
                "subject_id": row.plate_code,
                "subject_name": row.plate_name,
                "title": row.description or row.plate_name,
                "description": row.description,
                "jump_url": row.jump_url,
                "rank_no": row.rank_no,
                "driver": row.description,
                "attention_num": None,
                "stocks": [
                    {
                        "stock_code": stock.stock_code,
                        "stock_name": stock.stock_name,
                        "change_pct": stock.change_pct,
                        "last_price": stock.last_price,
                    }
                    for stock in stocks
                ],
            })
        return result

    def _daily_topics(self, trade_date: date) -> list[dict]:
        rows = (
            self.db.query(MktDailyTopic)
            .filter(MktDailyTopic.trade_date == trade_date)
            .order_by(MktDailyTopic.rank_no.asc(), MktDailyTopic.id.asc())
            .all()
        )
        result = []
        for row in rows:
            stocks = (
                self.db.query(MktDailyTopicStock)
                .filter(MktDailyTopicStock.topic_id == row.id)
                .order_by(MktDailyTopicStock.id.asc())
                .all()
            )
            result.append({
                "source": row.platform,
                "rank_no": row.rank_no,
                "topic_code": row.topic_code,
                "title": row.title,
                "description": row.description,
                "subtitle": row.subtitle,
                "hot_value": row.hot_value,
                "jump_url": row.jump_url,
                "stocks": [
                    {
                        "stock_code": stock.stock_code,
                        "stock_name": stock.stock_name,
                        "change_pct": stock.change_pct,
                    }
                    for stock in stocks
                ],
            })
        return result

    def _limit_up_ladder(self, trade_date: date) -> list[dict]:
        rows = (
            self.db.query(MktLimitUpStock)
            .filter(MktLimitUpStock.trade_date == trade_date)
            .all()
        )
        grouped: dict[int, list[MktLimitUpStock]] = {}
        for row in rows:
            height = row.ladder_height or row.board_count or 1
            grouped.setdefault(height, []).append(row)
        return [
            {
                "height": height,
                "count": len(stocks),
                "stocks": [
                    {"stock_code": stock.stock_code, "stock_name": stock.stock_name}
                    for stock in sorted(stocks, key=lambda item: (item.limit_datetime is None, item.limit_datetime, item.stock_code))
                ],
            }
            for height, stocks in sorted(grouped.items(), key=lambda item: item[0], reverse=True)
        ]

    def get_limit_up_ladder(self, trade_date: date) -> list[dict]:
        return self._limit_up_ladder(trade_date)

    def get_market_overview(self, trade_date: date) -> dict:
        row = (
            self.db.query(MktDaily)
            .filter(MktDaily.trade_date == trade_date, MktDaily.source == "real")
            .order_by(MktDaily.collected_at.desc())
            .first()
        ) or (
            self.db.query(MktDaily)
            .filter(MktDaily.trade_date == trade_date)
            .order_by(MktDaily.collected_at.desc())
            .first()
        )
        if not row:
            return {"trade_date": trade_date.isoformat(), "items": [], "note": "当前日期暂无市场数据"}

        # Compute index change from previous trading day
        prev_row = (
            self.db.query(MktDaily)
            .filter(MktDaily.trade_date < trade_date)
            .order_by(MktDaily.trade_date.desc())
            .first()
        )
        def calc_index_change(current: float | None, previous: float | None) -> float | None:
            if current is None or previous is None or previous == 0:
                return None
            return round((current - previous) / previous * 100, 2)

        sh_index_change_pct = (
            row.sh_index_change_pct
            if row.sh_index_change_pct is not None
            else calc_index_change(row.sh_index, prev_row.sh_index if prev_row else None)
        )
        sz_index_change_pct = (
            row.sz_index_change_pct
            if row.sz_index_change_pct is not None
            else calc_index_change(row.sz_index, prev_row.sz_index if prev_row else None)
        )
        cyb_index_change_pct = (
            row.cyb_index_change_pct
            if row.cyb_index_change_pct is not None
            else calc_index_change(row.cyb_index, prev_row.cyb_index if prev_row else None)
        )

        total = (row.up_count or 0) + (row.down_count or 0) + (row.flat_count or 0)
        up_ratio = row.up_count / total if total else 0
        # Generate commentary
        parts = []
        if row.sh_index and row.sh_index > 0:
            change_str = f"{sh_index_change_pct:+.2f}%" if sh_index_change_pct is not None else ""
            parts.append(f"上证指数 {row.sh_index:.0f} 点{(' ' + change_str) if change_str else ''}")
            parts.append("市场普涨，情绪积极")
        elif up_ratio >= 0.5:
            parts.append("市场分化，涨跌互现")
        elif up_ratio >= 0.3:
            parts.append("市场偏弱，多数个股下跌")
        else:
            parts.append("市场弱势，注意风险控制")
        if row.total_amount:
            amt = row.total_amount / 10000
            if amt > 2:
                parts.append(f"成交额 {amt:.2f} 万亿，交投活跃")
            elif amt > 1:
                parts.append(f"成交额 {amt:.2f} 万亿，交投正常")
            else:
                parts.append(f"成交额 {amt:.2f} 万亿，交投低迷")
        if row.limit_up_count:
            parts.append(f"涨停 {row.limit_up_count} 家")
            if row.max_continue_board and row.max_continue_board >= 4:
                parts.append(f"最高连板 {row.max_continue_board} 板，短线情绪较高")
        if row.limit_down_count and row.limit_down_count > 10:
            parts.append(f"跌停 {row.limit_down_count} 家，注意风险释放")

        market_comment = "；".join(parts) + "。仅作为交易辅助，请结合个人交易规则确认。"

        return {
            "trade_date": row.trade_date.isoformat(),
            "source": row.source,
            "sh_index": row.sh_index,
            "sz_index": row.sz_index,
            "cyb_index": row.cyb_index,
            "index_change_pct": sh_index_change_pct,
            "sh_index_change_pct": sh_index_change_pct,
            "sh_index_change_px": row.sh_index_change_px,
            "sz_index_change_pct": sz_index_change_pct,
            "sz_index_change_px": row.sz_index_change_px,
            "cyb_index_change_pct": cyb_index_change_pct,
            "cyb_index_change_px": row.cyb_index_change_px,
            "index_trade_status": row.index_trade_status or {},
            "today_chances": self._daily_chances(row.trade_date),
            "today_tuyeres": self._daily_tuyeres(row.trade_date),
            "topic_list": self._daily_topics(row.trade_date),
            "limit_up_ladder": self._limit_up_ladder(row.trade_date),
            "total_amount": row.total_amount,
            "up_count": row.up_count,
            "down_count": row.down_count,
            "flat_count": row.flat_count,
            "limit_up_count": row.limit_up_count,
            "limit_down_count": row.limit_down_count,
            "broken_limit_count": row.broken_limit_count,
            "max_continue_board": row.max_continue_board,
            "source_url": row.source_url,
            "source_update_time": row.source_update_time,
            "collected_at": row.collected_at,
            "market_comment": market_comment,
        }

    def get_hot_boards(self, trade_date: date | None = None, platform: str | None = None) -> list[dict]:
        if trade_date:
            query = self.db.query(MktDailyPlate).filter(
                MktDailyPlate.trade_date == trade_date,
                MktDailyPlate.plate_type == "limit_up",
            )
            if platform:
                query = query.filter(MktDailyPlate.platform == platform)
            query = query.filter(
                ~MktDailyPlate.plate_name.like("%ST%"),
                MktDailyPlate.plate_name != "其他",
                MktDailyPlate.plate_name != "其它",
                MktDailyPlate.plate_name != "未分类",
            )
            result = []
            for index, row in enumerate(query.order_by(MktDailyPlate.rank_no.asc(), MktDailyPlate.id.asc()).limit(3).all(), start=1):
                item = self._daily_plate_board_dict(row, index)
                related_count = self.db.query(MktDailyPlateStock).filter(MktDailyPlateStock.plate_id == row.id).count()
                item["raw_score"] = related_count
                item["limit_up_count"] = related_count
                result.append(item)
            return result

        query = self.db.query(MktDailyPlate).filter(MktDailyPlate.plate_type.in_(["limit_up", "hot_board"]))
        if trade_date:
            query = query.filter(MktDailyPlate.trade_date == trade_date)
        else:
            latest = (
                self.db.query(MktDailyPlate.trade_date)
                .filter(MktDailyPlate.plate_type.in_(["limit_up", "hot_board"]))
                .order_by(MktDailyPlate.trade_date.desc())
                .first()
            )
            if latest:
                query = query.filter(MktDailyPlate.trade_date == latest[0])
        if platform:
            query = query.filter(MktDailyPlate.platform == platform)
        return [
            self._daily_plate_board_dict(row, index)
            for index, row in enumerate(query.order_by(MktDailyPlate.rank_no.asc(), MktDailyPlate.id.asc()).limit(5).all(), start=1)
        ]

    def get_hot_stocks(self, trade_date: date | None = None) -> list[dict]:
        query = self.db.query(MktHotStock)
        if trade_date:
            query = query.filter(MktHotStock.trade_date == trade_date)
        rows = query.order_by(MktHotStock.score.desc(), MktHotStock.id).all()
        return [self._hot_stock_dict(row) for row in rows]

    def get_limit_ups(self, trade_date: date | None = None, platform: str | None = None) -> list[dict]:
        stock_query = self.db.query(MktLimitUpStock)
        if trade_date:
            stock_query = stock_query.filter(MktLimitUpStock.trade_date == trade_date)
        if platform:
            stock_query = stock_query.filter(MktLimitUpStock.platform == platform)
        stock_rows = stock_query.order_by(MktLimitUpStock.limit_time, MktLimitUpStock.stock_code).all()
        return [self._limit_up_stock_dict(row) for row in stock_rows]

    def get_stock_source_summary(self, stock_code: str, trade_date: date) -> dict:
        code = self._hot_stock_code(stock_code)
        hot = self.db.query(MktHotStock).filter_by(stock_code=code, trade_date=trade_date).all()
        limit_stock_rows = self.db.query(MktLimitUpStock).filter_by(stock_code=code, trade_date=trade_date).all()
        return {
            "stock_code": code,
            "hot_sources": [self._hot_stock_dict(item) for item in hot],
            "limit_sources": [self._limit_up_stock_dict(item) for item in limit_stock_rows],
            "xueqiu_url": xueqiu_link(code),
        }

    def get_latest_source(self, stock_code: str) -> dict:
        code = self._hot_stock_code(stock_code)
        hot = self.db.query(MktHotStock).filter_by(stock_code=code).order_by(MktHotStock.trade_date.desc()).first()
        limit_stock_row = self.db.query(MktLimitUpStock).filter_by(stock_code=code).order_by(MktLimitUpStock.trade_date.desc()).first()
        return {
            "stock_code": code,
            "latest_hot": self._hot_stock_dict(hot) if hot else None,
            "latest_limit": self._limit_up_stock_dict(limit_stock_row) if limit_stock_row else None,
            "xueqiu_url": xueqiu_link(code),
        }

    @staticmethod
    def _daily_plate_board_dict(row: MktDailyPlate, rank_no: int) -> dict:
        return {
            "id": row.id,
            "trade_date": row.trade_date,
            "platform": row.platform,
            "board_name": row.plate_name,
            "plate_code": row.plate_code,
            "plate_name": row.plate_name,
            "platform_rank": rank_no,
            "raw_score": None,
            "limit_up_count": None,
            "change_pct": None,
            "reason": row.description,
            "up_reason": row.description,
            "source_update_time": None,
            "collected_at": row.created_at,
        }

    @staticmethod
    def _hot_stock_dict(row: MktHotStock) -> dict:
        return {
            "id": row.id,
            "trade_date": row.trade_date,
            "stock_code": row.stock_code,
            "stock_name": row.stock_name,
            "assoc_plate": row.assoc_plate,
            "sector_name": row.assoc_plate,
            "board_name": row.assoc_plate,
            "cls_rank": row.cls_rank,
            "ths_rank": row.ths_rank,
            "tgb_rank": row.tgb_rank,
            "price": row.price,
            "change_pct": row.change_pct,
            "reason": row.reason,
            "raw_reason": row.reason,
            "tag": row.tag,
            "score": row.score,
            "raw_score": row.score,
            "created_at": row.created_at,
        }

    @staticmethod
    def _limit_up_stock_dict(row: MktLimitUpStock) -> dict:
        return {
            "id": row.id,
            "trade_date": row.trade_date,
            "platform": row.platform,
            "raw_secu_code": row.raw_secu_code,
            "stock_code": row.stock_code,
            "stock_name": row.stock_name,
            "limit_time": str(row.limit_time or "").split(" ")[-1][:5] or row.limit_time,
            "limit_datetime": row.limit_datetime,
            "last_limit_time": row.limit_time,
            "open_limit_count": None,
            "seal_amount": None,
            "seal_volume": None,
            "turnover_rate": None,
            "amount": None,
            "board_count": row.board_count or row.ladder_height or 1,
            "board_days": row.board_days,
            "board_text": row.board_text,
            "concept": row.plate_name,
            "limit_reason": row.limit_reason,
            "limit_type": row.reason_tags,
            "source_url": None,
            "source_update_time": row.source_update_time,
            "collected_at": row.collected_at,
            "change_pct": row.change_pct,
            "last_price": row.last_price,
            "ladder_height": row.ladder_height,
            "plate_code": row.plate_code,
            "plate_name": row.plate_name,
        }


class PrdWatchPoolService:
    ACTIVE_STATUSES = [
        "watching",
        "signal_generated",
        "waiting_buy_point",
        "buy_pending_confirm",
        "trading",
        "sell_signal_pending",
        "sell_delayed",
    ]
    TERMINAL_STATUSES = {"sold", "pending_review", "archived", "invalid", "blacklist", "removed"}
    TRADING_SYSTEMS = {"platform_breakout", "uptrend", "relay"}
    VALID_TRANSITIONS = {
        None: {"watching", "blacklist"},
        "watching": {"signal_generated", "waiting_buy_point", "buy_pending_confirm", "trading", "invalid", "blacklist", "removed", "archived"},
        "signal_generated": {"waiting_buy_point", "buy_pending_confirm", "trading", "invalid", "blacklist", "removed", "watching"},
        "waiting_buy_point": {"buy_pending_confirm", "signal_generated", "invalid", "blacklist", "removed", "watching"},
        "buy_pending_confirm": {"trading", "waiting_buy_point", "invalid", "blacklist", "removed"},
        "trading": {"sell_signal_pending", "sell_delayed", "sold", "pending_review", "blacklist"},
        "sell_signal_pending": {"sell_delayed", "sold", "pending_review", "trading"},
        "sell_delayed": {"sell_signal_pending", "sold", "pending_review", "trading"},
        "sold": {"pending_review", "archived"},
        "pending_review": {"archived"},
        "invalid": {"watching", "archived", "blacklist"},
        "removed": {"watching", "blacklist"},
        "blacklist": {"watching"},
        "archived": {"watching"},
    }

    def __init__(self, db: Session):
        self.db = db

    def list_watch_pool(self, status_filter: str | None = None) -> list[WatchPool]:
        query = self.db.query(WatchPool)
        if status_filter:
            query = query.filter(WatchPool.status == status_filter)
        else:
            query = query.filter(WatchPool.active.is_(True))
        return query.order_by(WatchPool.created_at.desc()).all()

    def add_watch(self, payload: dict) -> WatchPool:
        code = normalize_stock_code(payload["stock_code"])
        self._validate_required_add_payload(payload)
        system_context = self._build_system_context(payload)
        existing = self.get_effective_watch(code)
        if existing:
            return self.update_watch(existing.id, payload)

        blacklist = self._get_blacklist_watch(code)
        if blacklist and payload.get("confirm_blacklist_risk") is not True:
            raise ValueError("blacklist confirmation required")
        if blacklist and payload.get("confirm_blacklist_risk") is True:
            self._apply_watch_payload(blacklist, payload)
            self.transition(
                blacklist.id,
                "watching",
                payload.get("entry_reason") or payload.get("reason") or "restore from blacklist",
                operation_type="restore_from_blacklist",
                snapshot={"payload": self._safe_payload(payload), "confirmed_blacklist_risk": True},
            )
            self.db.refresh(blacklist)
            return blacklist

        entry_source = payload.get("entry_source") or "manual"
        entry_reason = payload.get("entry_reason") or payload.get("reason") or ""
        key_observe_price = payload.get("key_observe_price", payload.get("entry_price"))
        auto_remove_price = payload.get("auto_remove_price")
        trading_system = system_context["trading_system"] or payload["trading_system"]
        system_params = system_context["system_params"]
        entity = WatchPool(
            stock_code=code,
            stock_name=payload.get("stock_name") or code,
            sector_name=payload.get("sector_name") or payload.get("board_name"),
            reason=entry_reason,
            entry_reason=entry_reason,
            entry_source=entry_source,
            trading_system=trading_system,
            trading_system_code=system_context["trading_system_code"],
            system_stage=payload.get("system_stage") or "observe",
            system_params_json=system_params,
            active_rule_codes_json=system_context["active_rule_codes"],
            next_action=payload.get("next_action") or self._default_next_action(payload.get("system_stage") or "observe"),
            system_recommendation=payload.get("system_recommendation") or self.recommend_trading_system(entry_source, payload),
            key_observe_price=system_params.get("key_observe_price", key_observe_price),
            auto_remove_price=None if auto_remove_price in {None, ""} else float(auto_remove_price),
            invalid_condition=system_params.get("invalid_condition", payload.get("invalid_condition")),
            risk_tags=payload.get("risk_tags") or [],
            signal_enabled=payload.get("signal_enabled", True),
            latest_signal_id=payload.get("latest_signal_id"),
            user_remark=payload.get("user_remark") or payload.get("remark") or "",
            labels=payload.get("labels") or [],
            monitor_enabled=True,
            operation_strategies=[],
            buy_point_types=[],            entry_price=key_observe_price,
            remark=payload.get("user_remark") or payload.get("remark") or "",
            added_trade_date=date.today(),
            active=True,        )
        self.db.add(entity)
        self.db.flush()
        self._log(
            entity,
            None,
            "watching",
            entry_reason,
            operation_type="add_watch",
            snapshot={"payload": self._safe_payload(payload), "watch": self._snapshot(entity)},
        )
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update_watch(self, watch_id: int, payload: dict) -> WatchPool:
        entity = self.get_watch(watch_id)
        before_status = entity.status or entity.status
        self._apply_watch_payload(entity, payload)
        after_status = entity.status or entity.status
        if before_status != after_status:
            self.validate_transition(before_status, after_status)
        self._log(
            entity,
            before_status,
            after_status,
            payload.get("adjust_reason") or payload.get("entry_reason") or payload.get("reason") or "update watch",
            operation_type="update_watch",
            snapshot={"payload": self._safe_payload(payload), "watch": self._snapshot(entity)},
        )
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_watch(self, watch_id: int) -> WatchPool:
        entity = self.db.query(WatchPool).filter(WatchPool.id == watch_id).first()
        if not entity:
            raise ValueError("watch not found")
        return entity

    def remove_watch(self, watch_id: int, reason: str) -> WatchPool:
        return self.transition(watch_id, "removed", reason, operation_type="remove_watch")

    def hard_delete_watch(self, watch_id: int) -> dict:
        entity = self.get_watch(watch_id)
        signal_ids = [
            row[0]
            for row in self.db.query(WatchSignal.signal_id)
            .filter(WatchSignal.watch_id == watch_id)
            .all()
        ]
        trade_ids = [
            row[0]
            for row in self.db.query(WatchTrade.id)
            .filter(WatchTrade.watch_id == watch_id)
            .all()
        ]
        deleted = {
            "watch_id": watch_id,
            "stock_code": entity.stock_code,
            "stock_name": entity.stock_name,
            "signals": len(signal_ids),
            "trades": len(trade_ids),
        }
        if signal_ids:
            self.db.query(WatchSignalPerformance).filter(WatchSignalPerformance.signal_id.in_(signal_ids)).delete(synchronize_session=False)
            self.db.query(WatchSignal).filter(WatchSignal.signal_id.in_(signal_ids)).delete(synchronize_session=False)
        if trade_ids:
            self.db.query(WatchTradeExecution).filter(WatchTradeExecution.trade_id.in_(trade_ids)).delete(synchronize_session=False)
            self.db.query(ReviewTrade).filter(ReviewTrade.trade_id.in_(trade_ids)).delete(synchronize_session=False)
            self.db.query(WatchTrade).filter(WatchTrade.id.in_(trade_ids)).delete(synchronize_session=False)
        self.db.query(WatchPoolStatusLog).filter(WatchPoolStatusLog.watch_id == watch_id).delete(synchronize_session=False)
        self.db.delete(entity)
        self.db.commit()
        return deleted

    def restore_watch(self, watch_id: int) -> WatchPool:
        return self.transition(watch_id, "watching", "restore to watching", operation_type="restore_watch")

    def blacklist_watch(self, watch_id: int, reason: str) -> WatchPool:
        return self.transition(watch_id, "blacklist", reason, operation_type="blacklist_watch")

    def unblacklist_watch(self, watch_id: int, reason: str) -> WatchPool:
        return self.transition(watch_id, "watching", reason, operation_type="unblacklist_watch")

    def set_monitor(self, watch_id: int, enabled: bool, reason: str = "") -> WatchPool:
        entity = self.get_watch(watch_id)
        entity.monitor_enabled = enabled
        entity.signal_enabled = enabled
        self._log(
            entity,
            entity.status or entity.status,
            entity.status or entity.status,
            reason or ("enable monitor" if enabled else "disable monitor"),
            operation_type="set_monitor",
            snapshot={"monitor_enabled": enabled, "watch": self._snapshot(entity)},
        )
        self.db.commit()
        return entity

    def summary(self) -> dict:
        statuses = [*self.ACTIVE_STATUSES, *sorted(self.TERMINAL_STATUSES)]
        return {status: self.db.query(WatchPool).filter(WatchPool.status == status).count() for status in statuses}

    def logs(self, watch_id: int) -> list[WatchPoolStatusLog]:
        return (
            self.db.query(WatchPoolStatusLog)
            .filter(WatchPoolStatusLog.watch_id == watch_id)
            .order_by(WatchPoolStatusLog.operated_at.desc())
            .all()
        )

    def transition(
        self,
        watch_id: int,
        to_status: str,
        reason: str,
        operator_type: str = "user",
        operation_type: str = "status_transition",
        snapshot: dict | None = None,
    ) -> WatchPool:
        entity = self.get_watch(watch_id)
        from_status = entity.status or entity.status
        self.validate_transition(from_status, to_status)
        entity.status = to_status
        entity.status = to_status
        if to_status in {"removed", "archived", "invalid", "blacklist"}:
            entity.active = False
        if to_status == "watching":
            entity.active = True
            entity.monitor_enabled = True
            entity.signal_enabled = True
        if to_status == "blacklist":
            entity.monitor_enabled = False
            entity.signal_enabled = False
        if to_status in {"removed", "archived", "invalid"}:
            entity.archive_reason = reason
            entity.monitor_enabled = False
            entity.signal_enabled = False
        self._log(
            entity,
            from_status,
            to_status,
            reason,
            operator_type=operator_type,
            operation_type=operation_type,
            snapshot=snapshot or self._snapshot(entity),
        )
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def validate_transition(self, from_status: str | None, to_status: str) -> bool:
        if from_status == to_status:
            return True
        allowed = self.VALID_TRANSITIONS.get(from_status)
        if allowed is None and from_status not in self.VALID_TRANSITIONS:
            allowed = set(self.ACTIVE_STATUSES) | self.TERMINAL_STATUSES
        if to_status not in (allowed or set()):
            raise ValueError(f"invalid watch lifecycle transition: {from_status} -> {to_status}")
        return True

    def mark_invalid(self, watch_id: int, payload: dict | str) -> WatchPool:
        if isinstance(payload, str):
            reason = payload
            snapshot = {"reason": reason}
        else:
            reason = payload.get("invalid_reason") or payload.get("reason") or "watch invalid"
            snapshot = self._safe_payload(payload)
        return self.transition(watch_id, "invalid", reason, operation_type="mark_invalid", snapshot=snapshot)

    def get_effective_watch(self, stock_code: str) -> WatchPool | None:
        code = normalize_stock_code(stock_code)
        return (
            self.db.query(WatchPool)
            .filter(
                WatchPool.stock_code == code,
                WatchPool.active.is_(True),
                WatchPool.status.in_(self.ACTIVE_STATUSES) | WatchPool.status.in_(self.ACTIVE_STATUSES),
            )
            .order_by(WatchPool.updated_at.desc(), WatchPool.created_at.desc())
            .first()
        )

    def recommend_trading_system(self, entry_source: str | None = None, payload: dict | None = None) -> str:
        payload = payload or {}
        text = " ".join(str(payload.get(key) or "") for key in ["entry_reason", "reason", "limit_reason", "board_name"])
        if entry_source == "limit_up" or "relay" in text.lower():
            return "relay"
        if "breakout" in text.lower() or "\u7a81\u7834" in text:
            return "platform_breakout"
        return "uptrend"

    def _validate_required_add_payload(self, payload: dict) -> None:
        trading_system_value = payload.get("trading_system_code") or payload.get("trading_system")
        if trading_system_value and "trading_system" not in payload:
            payload["trading_system"] = trading_system_value
        required = ["trading_system", "entry_reason"]
        if not payload.get("trading_system_code"):
            required.extend(["key_observe_price", "invalid_condition"])
        missing = [key for key in required if payload.get(key) in (None, "")]
        if missing:
            raise ValueError(f"{missing[0]} is required")
        if payload.get("trading_system_code"):
            return
        if payload["trading_system"] not in self.TRADING_SYSTEMS:
            raise ValueError("trading_system is invalid")
        self._validate_positive_number(payload["key_observe_price"], "key_observe_price")

    def _build_system_context(self, payload: dict) -> dict:
        system_code = payload.get("trading_system_code")
        if not system_code:
            return {
                "trading_system": payload.get("trading_system"),
                "trading_system_code": None,
                "system_params": {},
                "active_rule_codes": payload.get("active_rule_codes_json") or [],
            }

        system = (
            self.db.query(TradingSystemDefinition)
            .filter(
                TradingSystemDefinition.system_code == system_code,
                TradingSystemDefinition.enabled.is_(True),
            )
            .first()
        )
        if not system:
            raise ValueError("trading_system_code is invalid")

        params = self._normalize_system_params(system_code, payload)
        active_rule_codes = payload.get("active_rule_codes_json")
        if active_rule_codes is None:
            active_rule_codes = [
                row.rule_code
                for row in (
                    self.db.query(TradingSystemRuleBinding)
                    .filter(
                        TradingSystemRuleBinding.system_code == system_code,
                        TradingSystemRuleBinding.enabled.is_(True),
                    )
                    .order_by(TradingSystemRuleBinding.stage.asc(), TradingSystemRuleBinding.sort_order.asc())
                    .all()
                )
            ]
        return {
            "trading_system": system_code,
            "trading_system_code": system_code,
            "system_params": params,
            "active_rule_codes": active_rule_codes or [],
        }

    def _normalize_system_params(self, system_code: str, payload: dict) -> dict:
        raw_params = payload.get("system_params_json") or payload.get("system_params") or {}
        if not isinstance(raw_params, dict):
            raise ValueError("system_params_json must be an object")
        params = dict(raw_params)
        if "key_observe_price" not in params and payload.get("key_observe_price") not in (None, ""):
            params["key_observe_price"] = payload.get("key_observe_price")
        if "invalid_condition" not in params and payload.get("invalid_condition") not in (None, ""):
            params["invalid_condition"] = payload.get("invalid_condition")
        if "auto_remove_price" not in params and payload.get("auto_remove_price") not in (None, ""):
            params["auto_remove_price"] = payload.get("auto_remove_price")

        definitions = (
            self.db.query(TradingSystemParamDefinition)
            .filter(
                TradingSystemParamDefinition.system_code == system_code,
                TradingSystemParamDefinition.enabled.is_(True),
            )
            .order_by(TradingSystemParamDefinition.sort_order.asc(), TradingSystemParamDefinition.param_id.asc())
            .all()
        )
        normalized: dict = {}
        for definition in definitions:
            value = params.get(definition.param_key)
            if definition.required and value in (None, ""):
                raise ValueError(f"{definition.param_key} is required")
            if value in (None, ""):
                if definition.default_value not in (None, ""):
                    normalized[definition.param_key] = definition.default_value
                continue
            if definition.param_type == "number":
                normalized[definition.param_key] = self._validate_positive_number(value, definition.param_key)
            elif definition.param_type == "boolean":
                normalized[definition.param_key] = bool(value)
            else:
                normalized[definition.param_key] = str(value).strip()
        return normalized

    @staticmethod
    def _validate_positive_number(value, key: str) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} must be positive") from exc
        if number <= 0:
            raise ValueError(f"{key} must be positive")
        return number

    @staticmethod
    def _default_next_action(stage: str) -> str:
        actions = {
            "observe": "等待观察条件和买点信号确认",
            "buy_confirm": "确认买点是否满足交易计划",
            "trading": "跟踪卖点、止损和风险提醒",
            "sell": "确认卖出处理并准备复盘",
            "stop_loss": "确认是否触发止损纪律",
        }
        return actions.get(stage, "继续按交易体系观察")

    def _get_blacklist_watch(self, stock_code: str) -> WatchPool | None:
        return (
            self.db.query(WatchPool)
            .filter(
                WatchPool.stock_code == stock_code,(WatchPool.status == "blacklist") | (WatchPool.status == "blacklist"),
            )
            .order_by(WatchPool.updated_at.desc(), WatchPool.created_at.desc())
            .first()
        )

    def _apply_watch_payload(self, entity: WatchPool, payload: dict) -> None:
        if "stock_code" in payload:
            entity.stock_code = normalize_stock_code(payload["stock_code"])
        simple_fields = [
            "stock_name",
            "sector_name",
            "labels",
            "monitor_enabled",
            "signal_enabled",
            "risk_tags",
            "latest_signal_id",
            "system_recommendation",
        ]
        for key in simple_fields:
            if key in payload:
                setattr(entity, key, payload[key])
        if "board_name" in payload and "sector_name" not in payload:
            entity.sector_name = payload["board_name"]
        if "trading_system" in payload and "trading_system_code" not in payload:
            if payload["trading_system"] not in self.TRADING_SYSTEMS:
                raise ValueError("trading_system is invalid")
            entity.trading_system = payload["trading_system"]
        if "trading_system_code" in payload:
            system_context = self._build_system_context(payload)
            entity.trading_system = system_context["trading_system"]
            entity.trading_system_code = system_context["trading_system_code"]
            entity.system_params_json = system_context["system_params"]
            entity.active_rule_codes_json = system_context["active_rule_codes"]
            entity.key_observe_price = system_context["system_params"].get("key_observe_price", entity.key_observe_price)
            entity.invalid_condition = system_context["system_params"].get("invalid_condition", entity.invalid_condition)
        if "system_stage" in payload:
            entity.system_stage = payload["system_stage"] or "observe"
        if "next_action" in payload:
            entity.next_action = payload["next_action"]
        if "entry_reason" in payload or "reason" in payload:
            entity.entry_reason = payload.get("entry_reason") or payload.get("reason")
            entity.reason = entity.entry_reason
        if "key_observe_price" in payload or "entry_price" in payload:
            entity.key_observe_price = payload.get("key_observe_price", payload.get("entry_price"))
            entity.entry_price = entity.key_observe_price
        if "auto_remove_price" in payload:
            value = payload.get("auto_remove_price")
            entity.auto_remove_price = None if value in {None, ""} else float(value)
        if "invalid_condition" in payload:
            entity.invalid_condition = payload["invalid_condition"]
        if "user_remark" in payload or "remark" in payload:
            val = payload.get("user_remark") or payload.get("remark") or ""
            entity.user_remark = val
            entity.remark = val
        if "status" in payload:
            entity.status = payload["status"]

    def _safe_payload(self, payload: dict) -> dict:
        return {key: value for key, value in payload.items() if key not in {"password", "token", "cookie", "secret"}}

    def _snapshot(self, entity: WatchPool) -> dict:
        return {
            "watch_id": entity.id,
            "stock_code": entity.stock_code,
            "stock_name": entity.stock_name,
            "status": entity.status,
            "status": entity.status,
            "trading_system": entity.trading_system,
            "trading_system_code": entity.trading_system_code,
            "system_stage": entity.system_stage,
            "system_params_json": entity.system_params_json or {},
            "active_rule_codes_json": entity.active_rule_codes_json or [],
            "next_action": entity.next_action,
            "entry_source": entity.entry_source,
            "entry_reason": entity.entry_reason,
            "key_observe_price": entity.key_observe_price,
            "auto_remove_price": entity.auto_remove_price,
            "invalid_condition": entity.invalid_condition,
            "risk_tags": entity.risk_tags or [],
            "signal_enabled": entity.signal_enabled,
            "monitor_enabled": entity.monitor_enabled,
        }

    def _log(
        self,
        entity: WatchPool,
        from_status: str | None,
        to_status: str,
        reason: str,
        operator_type: str = "user",
        operation_type: str = "status_transition",
        snapshot: dict | None = None,
    ) -> None:
        self.db.add(
            WatchPoolStatusLog(
                watch_id=entity.id,
                stock_code=entity.stock_code,
                from_status=from_status,
                to_status=to_status,
                change_reason=reason,
                operator_type=operator_type,
                operation_type=operation_type,
                snapshot=snapshot or self._snapshot(entity),
            )
        )


def record_operation(
    db: Session,
    operation_type: str,
    target_type: str,
    target_id: str = "",
    summary: str = "",
    payload: dict | None = None,
) -> None:
    db.add(
        ConfigOperationLog(
            operation_type=operation_type,
            target_type=target_type,
            target_id=str(target_id),
            summary=summary,
            payload=payload or {},
        )
    )
