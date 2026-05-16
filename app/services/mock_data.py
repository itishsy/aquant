from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    ConfigNotificationRecord,
    MktDaily,
    MktDailyPlate,
    MktDailyPlateStock,
    MktHotStock,
    MktLimitUpStock,
    ReviewForm,
    ReviewMonthly,
    ReviewTrade,
    ReviewWeekly,
    StockBasic,
    WatchPool,
    WatchPoolStatusLog,
    WatchSignal,
    WatchSignalPerformance,
    WatchTrade,
    WatchTradeExecution,
)
from app.services.normalization import xueqiu_link
from app.services.prd_v1 import ASSISTANT_NOTE, SeedService


class MockDataService:
    """Idempotent PRD v1 demo data for local development and smoke tests."""

    STOCKS = [
        ("603019.SH", "中科曙光", "算力"),
        ("002230.SZ", "科大讯飞", "AI 应用"),
        ("300750.SZ", "宁德时代", "新能源"),
        ("002594.SZ", "比亚迪", "新能源车"),
        ("601127.SH", "赛力斯", "新能源车"),
        ("600000.SH", "浦发银行", "金融"),
        ("000001.SZ", "平安银行", "金融"),
        ("688981.SH", "中芯国际", "半导体"),
        ("300308.SZ", "中际旭创", "光模块"),
        ("000977.SZ", "浪潮信息", "算力"),
        ("601318.SH", "中国平安", "金融"),
        ("430000.BJ", "北交样本", "北交所"),
    ]

    def __init__(self, db: Session):
        self.db = db

    def init_all(self, anchor: date | None = None) -> dict:
        SeedService(self.db).init_defaults()
        anchor = anchor or date.today()
        dates = [anchor, anchor - timedelta(days=1), anchor - timedelta(days=5)]
        counts = {
            "stock_basic": self._init_stock_basic(),
            "mkt_daily": self._init_market(dates),
            "mkt_daily_plate_hot_board": self._init_hot_boards(dates[0]),
            "mkt_hot_stock": self._init_hot_stocks(dates[0]),
            "mkt_limit_up_stock": self._init_limit_ups(dates[0]),
            "watch_pool": 0,
            "watch_signal": 0,
            "watch_trade": 0,
            "review": 0,
            "notification": 0,
        }
        watch_rows = self._init_watch_pool(dates[0])
        counts["watch_pool"] = len(watch_rows)
        counts["watch_signal"] = self._init_signals(watch_rows, dates[0])
        counts["watch_trade"] = self._init_trades(watch_rows)
        counts["review"] = self._init_reviews(dates[0])
        counts["notification"] = self._init_notifications()
        self.db.commit()
        return counts

    def _init_stock_basic(self) -> int:
        created = 0
        for code, name, sector in self.STOCKS:
            if not self.db.query(StockBasic).filter_by(stock_code=code).first():
                self.db.add(
                    StockBasic(
                        stock_code=code,
                        stock_name=name,
                        exchange=code.split(".")[-1],
                        sector=sector,
                    )
                )
                created += 1
        return created

    def _init_market(self, dates: list[date]) -> int:
        created = 0
        for idx, day in enumerate(dates):
            row = self.db.query(MktDaily).filter_by(trade_date=day, source="mock").first()
            if not row:
                row = MktDaily(trade_date=day, source="mock")
                self.db.add(row)
                created += 1
            row.sh_index = 3128.2 - idx * 12.3
            row.sz_index = 10122.5 - idx * 28.7
            row.cyb_index = 2016.3 - idx * 9.5
            row.index_change_pct = 0.62 - idx * 0.18
            row.total_amount = 11250.0 - idx * 420.0
            row.up_count = 3412 - idx * 180
            row.down_count = 1286 + idx * 170
            row.flat_count = 102
            row.limit_up_count = 68 - idx * 4
            row.limit_down_count = 3 + idx
            row.broken_limit_count = 9 + idx
            row.max_continue_board = 4
            row.source_url = "mock://market/daily"
            row.source_update_time = datetime.combine(day, datetime.min.time()).replace(hour=15, minute=30)
            row.raw_snapshot = {"source": "mock", "assistant_note": ASSISTANT_NOTE}
        return created

    def _init_hot_boards(self, day: date) -> int:
        created = 0
        rows = [
            ("财联社", "算力", 1, 92.0, "算力服务器和国产芯片方向活跃", "603019.SH", "中科曙光"),
            ("财联社", "AI 应用", 2, 86.0, "大模型应用侧热度延续", "002230.SZ", "科大讯飞"),
            ("财联社", "新能源车", 3, 80.0, "整车和零部件同步修复", "002594.SZ", "比亚迪"),
            ("同花顺", "半导体", 1, 90.0, "先进制程和国产替代热度上升", "688981.SH", "中芯国际"),
            ("同花顺", "光模块", 2, 84.0, "海外 AI 算力链需求预期改善", "300308.SZ", "中际旭创"),
            ("东方财富", "金融", 3, 70.0, "低估值板块轮动修复", "601318.SH", "中国平安"),
        ]
        for platform, name, rank, score, reason, leader_code, leader_name in rows:
            plate_code = f"mock-hot-board:{platform}:{rank}"
            row = self.db.query(MktDailyPlate).filter_by(
                trade_date=day,
                plate_type="hot_board",
                platform=platform,
                plate_code=plate_code,
            ).first()
            if not row:
                row = MktDailyPlate(
                    trade_date=day,
                    plate_type="hot_board",
                    platform=platform,
                    plate_code=plate_code,
                )
                self.db.add(row)
                created += 1
            row.rank_no = rank
            row.plate_name = name
            row.description = reason
            self.db.flush()
            existing_stock = self.db.query(MktDailyPlateStock).filter_by(plate_id=row.id, stock_code=leader_code).first()
            if not existing_stock:
                self.db.add(MktDailyPlateStock(
                    plate_id=row.id,
                    stock_code=leader_code,
                    stock_name=leader_name,
                    change_pct=round(4.5 - rank * 0.7, 2),
                ))
        return created

    def _init_hot_stocks(self, day: date) -> int:
        created = 0
        for rank, (code, name, sector) in enumerate(self.STOCKS[:10], start=1):
            stock_code = code.split(".")[-1].lower() + code.split(".")[0]
            row = self.db.query(MktHotStock).filter_by(trade_date=day, stock_code=stock_code).first()
            if not row:
                row = MktHotStock(trade_date=day, stock_code=stock_code, stock_name=name)
                self.db.add(row)
                created += 1
            row.stock_name = name
            row.assoc_plate = sector
            row.cls_rank = rank
            row.ths_rank = rank if rank <= 8 else None
            row.tgb_rank = rank if rank <= 6 else None
            row.price = round(18 + rank * 1.35, 2)
            row.change_pct = round(5.2 - rank * 0.35, 2)
            row.reason = f"{sector} 方向关注度较高。"
            row.tag = sector
            row.score = sum({1: 71, 2: 67, 3: 61, 4: 59, 5: 53, 6: 47, 7: 43, 8: 41, 9: 37, 10: 31}.get(r, 0) for r in [row.cls_rank, row.ths_rank, row.tgb_rank] if r)
        return created

    def _init_limit_ups(self, day: date) -> int:
        created = 0
        for rank, (code, name, sector) in enumerate(self.STOCKS[:10], start=1):
            platform = "mock"
            row = (
                self.db.query(MktLimitUpStock)
                .filter_by(trade_date=day, source="mock", platform=platform, stock_code=code)
                .first()
            )
            if not row:
                row = MktLimitUpStock(
                    trade_date=day,
                    source="mock",
                    platform=platform,
                    stock_code=code,
                    stock_name=name,
                )
                self.db.add(row)
                created += 1
            row.stock_name = name
            row.plate_name = sector
            row.raw_secu_code = code.replace(".", "").lower()
            row.limit_time = f"{9 + rank // 3:02d}:{30 + rank:02d}"
            row.limit_datetime = datetime.combine(day, datetime.min.time()).replace(hour=9 + rank // 3, minute=30 + rank)
            row.change_pct = round(10.0 - rank * 0.08, 2)
            row.last_price = round(18 + rank * 1.2, 2)
            row.board_days = rank if rank <= 3 else None
            row.board_count = 1 if rank > 3 else rank
            row.board_text = f"{row.board_days}天{row.board_count}板" if row.board_days else f"{row.board_count}板"
            row.limit_reason = f"{sector} 方向活跃，平台原始涨停原因。"
            row.reason_tags = "首板" if row.board_count == 1 else "连板"
            row.source_update_time = datetime.combine(day, datetime.min.time()).replace(hour=15, minute=20)
        return created

    def _init_watch_pool(self, day: date) -> list[WatchPool]:
        rows: list[WatchPool] = []
        samples = [
            ("603019.SH", "中科曙光", "算力", 37.8),
            ("002230.SZ", "科大讯飞", "AI 应用", 48.6),
        ]
        for code, name, sector, price in samples:
            row = (
                self.db.query(WatchPool)
                .filter(WatchPool.stock_code == code, WatchPool.pool_status.in_(["watching", "triggered", "holding"]))
                .first()
            )
            if not row:
                row = WatchPool(
                    stock_code=code,
                    stock_name=name,
                    sector_name=sector,
                    reason="开发演示：模拟用户手动添加自选",
                    labels=["人气"],
                    pool_status="watching",
                    monitor_enabled=True,
                    operation_strategies=["趋势交易"],
                    buy_point_types=["B15 底背离买点", "支撑买点"],
                    source_type="manual",
                    source_platform="mock",
                    source_reason="模拟用户从市场页查看后手动添加",
                    xueqiu_url=xueqiu_link(code),
                    entry_price=price,
                    added_trade_date=day,
                )
                self.db.add(row)
                self.db.flush()
                self.db.add(
                    WatchPoolStatusLog(
                        watch_id=row.id,
                        stock_code=code,
                        from_status=None,
                        to_status="watching",
                        change_reason="模拟用户手动添加",
                        operator_type="user",
                    )
                )
            rows.append(row)
        return rows

    def _init_signals(self, watch_rows: list[WatchPool], day: date) -> int:
        created = 0
        for row in watch_rows:
            signal = (
                self.db.query(WatchSignal)
                .filter_by(
                    stock_code=row.stock_code,
                    buy_point_type="B15 底背离买点",
                    signal_type="buy",
                    trigger_date=day,
                )
                .first()
            )
            if not signal:
                signal = WatchSignal(
                    watch_id=row.id,
                    stock_code=row.stock_code,
                    stock_name=row.stock_name,
                    signal_type="buy",
                    buy_point_type="B15 底背离买点",
                    strategy_name="macd_15m_bullish_divergence",
                    signal_level="B",
                    kline_period="15m",
                    trigger_time=datetime.combine(day, datetime.min.time()).replace(hour=14, minute=45),
                    trigger_date=day,
                    trigger_price=row.entry_price,
                    trigger_reason=f"买入观察信号：15 分钟底背离条件接近满足。{ASSISTANT_NOTE}",
                    risk_desc=f"若跌破支撑或数据缺失，信号失效。{ASSISTANT_NOTE}",
                    stop_loss_price=round((row.entry_price or 10) * 0.96, 2),
                    target_price=round((row.entry_price or 10) * 1.08, 2),
                    invalid_condition="跌破参考支撑或信号条件消失",
                    signal_status="未处理",
                    user_action="未处理",
                    raw_snapshot={"source": "mock", "watch_id": row.id},
                )
                self.db.add(signal)
                self.db.flush()
                self.db.add(
                    WatchSignalPerformance(
                        signal_id=signal.signal_id,
                        watch_id=row.id,
                        stock_code=row.stock_code,
                        trigger_price=signal.trigger_price,
                    )
                )
                created += 1
        return created

    def _init_trades(self, watch_rows: list[WatchPool]) -> int:
        if not watch_rows:
            return 0
        watch = watch_rows[0]
        trade = self.db.query(WatchTrade).filter_by(stock_code=watch.stock_code, trade_status="open").first()
        if trade:
            return 0
        trade = WatchTrade(
            watch_id=watch.id,
            stock_code=watch.stock_code,
            stock_name=watch.stock_name,
            trade_source="manual_demo",
            buy_point_type="B15 底背离买点",
            first_buy_time=datetime.utcnow() - timedelta(days=2),
            first_buy_price=watch.entry_price,
            total_buy_amount=100,
            average_buy_price=watch.entry_price,
            remaining_amount=100,
            position_ratio=0.1,
            stop_loss_price=round((watch.entry_price or 10) * 0.96, 2),
            target_price=round((watch.entry_price or 10) * 1.08, 2),
            trade_status="open",
            remark=f"开发演示交易，{ASSISTANT_NOTE}",
        )
        self.db.add(trade)
        self.db.flush()
        self.db.add(
            WatchTradeExecution(
                trade_id=trade.id,
                watch_id=watch.id,
                stock_code=watch.stock_code,
                stock_name=watch.stock_name,
                execution_type="buy",
                execution_time=trade.first_buy_time or datetime.utcnow(),
                execution_price=watch.entry_price or 0,
                execution_amount=100,
                execution_reason=f"用户人工确认买入记录。{ASSISTANT_NOTE}",
            )
        )
        return 1

    def _init_reviews(self, day: date) -> int:
        created = 0
        week_period = f"{day.isocalendar().year}-W{day.isocalendar().week:02d}"
        month_period = day.strftime("%Y-%m")
        specs = [
            ("weekly", week_period, "本周复盘", ReviewWeekly),
            ("monthly", month_period, "本月复盘", ReviewMonthly),
        ]
        for review_type, period, title, detail_cls in specs:
            form = self.db.query(ReviewForm).filter_by(review_type=review_type, review_period=period).first()
            if not form:
                form = ReviewForm(
                    review_type=review_type,
                    review_period=period,
                    status="待填写",
                    title=title,
                    system_summary=f"开发演示复盘表单。{ASSISTANT_NOTE}",
                )
                self.db.add(form)
                self.db.flush()
                created += 1
            if detail_cls is ReviewWeekly and not self.db.query(ReviewWeekly).filter_by(review_id=form.id).first():
                self.db.add(
                    ReviewWeekly(
                        review_id=form.id,
                        week_start=day - timedelta(days=day.weekday()),
                        week_end=day - timedelta(days=day.weekday()) + timedelta(days=4),
                        market_summary="本周市场数据为 Mock 展示数据。",
                    )
                )
            if detail_cls is ReviewMonthly and not self.db.query(ReviewMonthly).filter_by(review_id=form.id).first():
                self.db.add(ReviewMonthly(review_id=form.id, month=month_period, market_summary="本月市场数据为 Mock 展示数据。"))
        trade = self.db.query(WatchTrade).first()
        if trade and not self.db.query(ReviewTrade).filter_by(trade_id=trade.id).first():
            self.db.add(ReviewTrade(trade_id=trade.id, status="待填写", user_comment="", trade_score=80))
            created += 1
        return created

    def _init_notifications(self) -> int:
        row = (
            self.db.query(ConfigNotificationRecord)
            .filter_by(push_type="复盘提醒", target_type="review", target_id="demo", channel="site")
            .first()
        )
        if row:
            return 0
        self.db.add(
            ConfigNotificationRecord(
                push_type="复盘提醒",
                target_type="review",
                target_id="demo",
                channel="site",
                title="复盘提醒",
                content=f"有待填写复盘样例。{ASSISTANT_NOTE}",
                payload={"source": "mock"},
                send_status="unread",
            )
        )
        return 1
