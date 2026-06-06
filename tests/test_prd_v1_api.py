from datetime import date, datetime

import pytest

from app.models import ConfigDictionary, MktDailyPlate, MktDailyPlateStock, MktHotStock, MktLimitUpStock, ReviewForm, TradingRuleDefinition, TradingSystemDefinition, TradingSystemParamDefinition, TradingSystemRuleBinding, WatchPool, WatchPoolStatusLog, WatchSignal, WatchTrade
from app.rule_executors import get_executor
from app.services.prd_v1 import PrdWatchPoolService, SeedService
from app.services.tasks import TaskService


def test_common_xueqiu_url_enveloped(client):
    response = client.get("/api/common/stocks/603019.SH/xueqiu-url")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["code"] == "SUCCESS"
    assert payload["data"]["xueqiu_url"] == "https://xueqiu.com/S/sh603019"


def test_common_dictionaries_include_watch_pool_codes_and_are_idempotent(client, db_session):
    first = SeedService(db_session).init_defaults()
    count_after_first = db_session.query(ConfigDictionary).count()
    second = SeedService(db_session).init_defaults()
    count_after_second = db_session.query(ConfigDictionary).count()
    assert first["created"] > 0
    assert second["created"] == 0
    assert count_after_first == count_after_second

    response = client.get("/api/common/dictionaries")
    assert response.status_code == 200
    rows = response.json()["data"]
    by_type = {}
    for row in rows:
        assert "code" in row
        assert "label" in row
        by_type.setdefault(row["dict_type"], {})[row["code"]] = row["label"]

    assert by_type["trading_system"] == {
        "breakout": "突破",
        "uptrend": "趋势",
        "relay": "接力",
    }
    assert set(by_type["watch_lifecycle_status"]) == {
        "watching",
        "signal_generated",
        "waiting_buy_point",
        "buy_pending_confirm",
        "trading",
        "sell_signal_pending",
        "sell_delayed",
        "sold",
        "pending_review",
        "archived",
        "invalid",
        "blacklist",
        "removed",
    }
    for dict_type in ["watch_invalid_reason", "signal_abandon_reason", "sell_reason", "emotion_state", "risk_tag"]:
        assert dict_type in by_type
        assert by_type[dict_type]
    forbidden_types = {"daily_trade_plan", "strict_mode", "watch_score", "market_score", "auto_add_candidates"}
    assert forbidden_types.isdisjoint(by_type)


def test_trading_system_seed_data_is_idempotent(db_session):
    first = SeedService(db_session).init_defaults()
    counts_after_first = {
        "systems": db_session.query(TradingSystemDefinition).count(),
        "params": db_session.query(TradingSystemParamDefinition).count(),
        "rules": db_session.query(TradingRuleDefinition).count(),
        "bindings": db_session.query(TradingSystemRuleBinding).count(),
    }
    second = SeedService(db_session).init_defaults()
    counts_after_second = {
        "systems": db_session.query(TradingSystemDefinition).count(),
        "params": db_session.query(TradingSystemParamDefinition).count(),
        "rules": db_session.query(TradingRuleDefinition).count(),
        "bindings": db_session.query(TradingSystemRuleBinding).count(),
    }

    assert first["created"] > 0
    assert second["created"] == 0
    assert counts_after_first == counts_after_second
    assert counts_after_first == {"systems": 4, "params": 3, "rules": 17, "bindings": 15}

    systems = {row.system_code: row.system_name for row in db_session.query(TradingSystemDefinition).all()}
    assert systems == {
        "breakout": "突破",
        "uptrend": "趋势",
        "relay": "接力",
        "rebound": "反弹",
    }

    platform_params = {
        row.param_key: (row.param_name, row.param_type, row.required)
        for row in db_session.query(TradingSystemParamDefinition).filter_by(system_code="breakout").all()
    }
    assert platform_params == {
        "platform_support_price": ("支撑位", "number", True),
        "key_observe_price": ("目标价", "number", True),
        "auto_remove_price": ("自动剔除价", "number", False),
    }

    rules = {
        row.rule_code: (row.rule_type, row.timeframe, row.executor_key)
        for row in db_session.query(TradingRuleDefinition).all()
    }
    assert rules["b5_divergence"] == ("buy_signal", "5m", "macd_bottom_divergence")
    assert rules["b15_divergence"] == ("buy_signal", "15m", "macd_bottom_divergence")
    assert rules["m5_top_divergence"] == ("sell_signal", "5m", "macd_top_divergence")
    assert rules["m30_dead_cross"] == ("sell_signal", "30m", "macd_dead_cross")
    assert rules["break_platform_support"] == ("stop_loss", "daily", "break_level")
    expected_generic_rules = {
        "observe_break_key_price": ("observe_risk", "daily", "break_level"),
        "observe_close_break_platform_support": ("invalid_signal", "daily", "break_level"),
        "observe_break_ma5": ("observe_risk", "daily", "break_ma"),
        "observe_break_ma10": ("observe_risk", "daily", "break_ma"),
        "observe_break_ma20": ("invalid_signal", "daily", "break_ma"),
        "observe_pullback_recent_high": ("observe_risk", "daily", "pullback_to_level"),
    }
    for rule_code, expected in expected_generic_rules.items():
        assert rules[rule_code] == expected
        assert get_executor(expected[2]) is not None

    bindings = {
        (row.stage, row.rule_code): (row.required, row.logic_group, row.logic_operator, row.enabled, row.config_json)
        for row in db_session.query(TradingSystemRuleBinding).filter_by(system_code="breakout").all()
    }
    assert bindings[("observe", "b5_divergence")][:4] == (False, "bottom_divergence", "OR", True)
    assert bindings[("observe", "b15_divergence")][:4] == (False, "bottom_divergence", "OR", True)
    assert bindings[("trading", "m5_top_divergence")][:4] == (False, "sell_signal", "OR", True)
    assert bindings[("trading", "m30_dead_cross")][:4] == (False, "sell_signal", "OR", True)
    assert bindings[("stop_loss", "break_platform_support")][:4] == (False, "stop_loss", "OR", True)
    assert bindings[("observe", "observe_break_key_price")][3] is False
    assert bindings[("observe", "observe_break_key_price")][4]["signal"]["target_param"] == "key_observe_price"
    assert bindings[("observe", "observe_break_ma5")][3] is False
    assert bindings[("observe", "observe_break_ma5")][4]["signal"] == {"ma": 5, "break_type": "cross_down"}
    assert bindings[("observe", "observe_pullback_recent_high")][3] is False
    assert bindings[("observe", "observe_pullback_recent_high")][4]["signal"]["mode"] == "from_recent_high"


def test_admin_trading_system_readonly_endpoints(client):
    headers = {"X-Admin-Token": "dev-admin-token"}

    systems_response = client.get("/api/admin/trading-systems", headers=headers)
    assert systems_response.status_code == 200
    systems = systems_response.json()["data"]
    assert [row["system_code"] for row in systems] == ["breakout", "uptrend", "relay", "rebound"]

    detail_response = client.get("/api/admin/trading-systems/breakout", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["system_name"] == "突破"

    rules_response = client.get("/api/admin/trading-rules", headers=headers)
    assert rules_response.status_code == 200
    rule_codes = {row["rule_code"] for row in rules_response.json()["data"]}
    assert "b5_divergence" in rule_codes
    assert "break_platform_support" in rule_codes

    params_response = client.get("/api/admin/trading-systems/breakout/params", headers=headers)
    assert params_response.status_code == 200
    assert [row["param_key"] for row in params_response.json()["data"]] == [
        "platform_support_price",
        "key_observe_price",
        "auto_remove_price",
    ]

    bindings_response = client.get("/api/admin/trading-systems/breakout/rules", headers=headers)
    assert bindings_response.status_code == 200
    bindings = bindings_response.json()["data"]
    assert len(bindings) == 11
    assert bindings[0]["rule"] is not None
    assert {row["rule_code"] for row in bindings} >= {"observe_break_key_price", "observe_break_ma5", "observe_pullback_recent_high"}
    assert {row["stage"] for row in bindings} == {"observe", "trading", "stop_loss"}


def test_h5_market_uses_raw_hot_stock_fields(client, db_session):
    trade_date = date(2026, 4, 24)
    db_session.add(
        MktHotStock(
            trade_date=trade_date,
            stock_code="sh603019",
            stock_name="中科曙光",
            assoc_plate="算力",
            cls_rank=1,
            price=49.5,
            change_pct=3.2,
            reason="平台原始原因",
            score=71,
            tag="算力",
        )
    )
    db_session.add(
        MktLimitUpStock(
            trade_date=trade_date,
            source="mock",
            platform="mock",
            stock_code="603019.SH",
            stock_name="中科曙光",
            plate_name="测试板块",
            raw_secu_code="sh603019",
            board_days=3,
            board_count=2,
            board_text="3天2板",
            ladder_height=2,
            limit_reason="平台涨停原因",
        )
    )
    db_session.flush()
    plate = MktDailyPlate(
        trade_date=trade_date,
        plate_type="limit_up",
        platform="mock",
        plate_code="p1",
        plate_name="AI应用",
        article_title="AI应用",
        description="涨停板块描述",
        jump_url="https://example.com/plate/p1",
        up_reason="上榜理由来自涨停板块表",
    )
    st_plate = MktDailyPlate(
        trade_date=trade_date,
        plate_type="limit_up",
        platform="mock",
        plate_code="p2",
        plate_name="ST板块",
        up_reason="应排除 ST",
    )
    db_session.add_all(
        [
            plate,
            st_plate,
        ]
    )
    db_session.flush()
    db_session.add(MktDailyPlateStock(plate_id=plate.id, stock_code="603019.SH", stock_name="中科曙光"))
    db_session.commit()

    response = client.get(f"/api/h5/market/hot-stocks?trade_date={trade_date}")
    assert response.status_code == 200
    item = response.json()["data"]["list"][0]
    assert item["cls_rank"] == 1
    assert item["raw_score"] == 71
    assert item["assoc_plate"] == "算力"
    assert "total_score" not in item

    limit_response = client.get(f"/api/h5/market/limit-ups?trade_date={trade_date}")
    assert limit_response.status_code == 200
    limit_data = limit_response.json()["data"]
    assert limit_data["list"][0]["limit_reason"] == "平台涨停原因"
    assert limit_data["list"][0]["board_text"] == "3天2板"
    assert limit_data["limit_up_ladder"][0]["height"] == 2
    assert limit_data["limit_up_ladder"][0]["count"] == 1

    board_response = client.get(f"/api/h5/market/hot-boards?trade_date={trade_date}&platform=mock")
    assert board_response.status_code == 200
    boards = board_response.json()["data"]["list"]
    assert boards[0]["board_name"] == "AI应用"
    assert boards[0]["limit_up_count"] == 1
    assert boards[0]["up_reason"] == "上榜理由来自涨停板块表"
    assert all("ST" not in item["board_name"] for item in boards)


def test_limit_up_collection_ignores_st_and_other_plates(monkeypatch, db_session):
    trade_date = date(2026, 5, 15)

    class FakeProvider:
        def get_limit_up_analysis(self, day):
            return {
                "plates": [
                    {"platform": "cls", "plate_code": "st", "plate_name": "ST\u80a1", "limit_up_count": 99, "up_reason": "ignored"},
                    {"platform": "cls", "plate_code": "other", "plate_name": "\u5176\u4ed6", "limit_up_count": 88, "up_reason": "ignored"},
                    {"platform": "cls", "plate_code": "ai", "plate_name": "AI", "limit_up_count": 7, "up_reason": "AI reason"},
                    {"platform": "cls", "plate_code": "robot", "plate_name": "Robot", "limit_up_count": 5, "up_reason": "Robot reason"},
                    {"platform": "cls", "plate_code": "chip", "plate_name": "Chip", "limit_up_count": 3, "up_reason": "Chip reason"},
                    {"platform": "cls", "plate_code": "low", "plate_name": "Low", "limit_up_count": 1, "up_reason": "Low reason"},
                ],
                "stocks": [
                    {"platform": "cls", "source": "real", "stock_code": "600001.SH", "stock_name": "A", "plate_code": "ai", "plate_name": "AI", "limit_reason": "AI reason"},
                    {"platform": "cls", "source": "real", "stock_code": "600002.SH", "stock_name": "B", "plate_code": "robot", "plate_name": "Robot"},
                    {"platform": "cls", "source": "real", "stock_code": "600003.SH", "stock_name": "C", "plate_code": "chip", "plate_name": "Chip"},
                    {"platform": "cls", "source": "real", "stock_code": "600004.SH", "stock_name": "D", "plate_code": "st", "plate_name": "ST\u80a1"},
                ],
            }

    monkeypatch.setattr("app.services.tasks.ProviderFactory.create", lambda: FakeProvider())
    log = TaskService(db_session).collect_limit_up_daily(trade_date)
    assert log.run_status == "success"

    rows = (
        db_session.query(MktDailyPlate)
        .filter(MktDailyPlate.trade_date == trade_date, MktDailyPlate.plate_type == "limit_up")
        .order_by(MktDailyPlate.rank_no.asc())
        .all()
    )
    assert [row.plate_name for row in rows] == ["AI", "Robot", "Chip"]
    assert [row.rank_no for row in rows] == [1, 2, 3]
    assert rows[0].description == "AI reason"
    assert db_session.query(MktDailyPlateStock).count() == 3


def test_hot_stock_collection_merges_platforms_and_requires_quote(monkeypatch, db_session):
    trade_date = date(2026, 5, 15)

    class FakeProvider:
        def get_hot_stock_rank(self, day):
            return [
                {"stock_code": "sh600001", "stock_name": "Alpha", "rank_field": "cls_rank", "rank": 1, "price": 10.0, "change_pct": 2.0, "reason": "cls reason", "tag": "cls tag"},
                {"stock_code": "600001.SH", "stock_name": "Alpha", "rank_field": "ths_rank", "rank": 2, "reason": "ths reason", "tag": "ths tag"},
                {"stock_code": "sz000003", "stock_name": "Gamma", "rank_field": "ths_rank", "rank": 4, "price": 0, "change_pct": 0, "reason": "", "tag": "zero quote"},
                {"stock_code": "sz000002", "stock_name": "Beta", "rank_field": "tgb_rank", "rank": 3, "reason": "skip no quote"},
            ]

        def get_stock_quote(self, stock_code):
            if stock_code == "sh600001":
                return {"price": 10.1, "change_pct": 2.1}
            if stock_code == "sz000003":
                return {"price": 8.8, "change_pct": 1.5}
            return {"price": None, "change_pct": None}

        def get_assoc_plates(self, stock_code):
            if stock_code == "sz000003":
                return [
                    {"plate_name": "Robot", "assoc_desc": "robot desc"},
                    {"plate_name": "Chip", "assoc_desc": "chip desc"},
                    {"plate_name": "IgnoredThird", "assoc_desc": "third desc"},
                ]
            return [{"plate_name": "AI应用", "assoc_desc": "assoc reason"}]

    db_session.add(MktDailyPlate(trade_date=trade_date, plate_type="chance", platform="cls", plate_code="p1", plate_name="AI应用"))
    db_session.add(MktHotStock(trade_date=trade_date, stock_code="sh600001", stock_name="Old", price=1, change_pct=1, reason="old", tag="old"))
    db_session.commit()

    monkeypatch.setattr("app.services.tasks.ProviderFactory.create", lambda: FakeProvider())
    log = TaskService(db_session).collect_hot_stock_rank(trade_date)
    assert log.run_status == "success"

    rows = db_session.query(MktHotStock).filter(MktHotStock.trade_date == trade_date).all()
    assert len(rows) == 2
    row = next(item for item in rows if item.stock_code == "sh600001")
    assert row.stock_code == "sh600001"
    assert row.cls_rank == 1
    assert row.ths_rank == 2
    assert row.tgb_rank is None
    assert row.price == 10.0
    assert row.change_pct == 2.0
    assert row.assoc_plate == "AI应用"
    assert "cls reason" in row.reason and "ths reason" in row.reason
    assert row.score == 138

    fallback = next(item for item in rows if item.stock_code == "sz000003")
    assert fallback.price == 8.8
    assert fallback.change_pct == 1.5
    assert fallback.assoc_plate == "Robot,Chip"
    assert "未匹配板块" not in fallback.assoc_plate


def test_h5_watch_pool_manual_add_only_and_idempotent(client):
    payload = {
        "stock_code": "603019.SH",
        "trading_system": "uptrend",
        "entry_reason": "manual watch reason",
        "key_observe_price": 50.0,
        "invalid_condition": "breaks support",
        "stock_name": "中科曙光",
        "labels": ["人气"],
        "operation_strategies": ["趋势交易"],
        "buy_point_types": ["B15 底背离买点"],
        
        
        
        
    }
    first = client.post("/api/h5/watch-pool", json=payload)
    second = client.post("/api/h5/watch-pool", json={**payload, "labels": ["趋势"]})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["watch_id"] == second.json()["data"]["watch_id"]
    assert second.json()["data"]["status"] == "watching"
    assert second.json()["data"]["monitor_enabled"] is True


def _watch_payload(**overrides):
    payload = {
        "stock_code": "603019.SH",
        "stock_name": "Aquant Test",
        "trading_system": "uptrend",
        "entry_reason": "manual selected from hot list",
        "key_observe_price": 50.0,
        "invalid_condition": "close below 48",
        
        "labels": ["trend"],
    }
    payload.update(overrides)
    return payload


def test_watch_pool_add_requires_trading_system(client):
    payload = _watch_payload()
    payload.pop("trading_system")
    response = client.post("/api/h5/watch-pool", json=payload)
    assert response.status_code == 400
    assert "trading_system" in response.json()["detail"]


def test_watch_pool_add_requires_key_observe_price(client):
    payload = _watch_payload()
    payload.pop("key_observe_price")
    response = client.post("/api/h5/watch-pool", json=payload)
    assert response.status_code == 400
    assert "key_observe_price" in response.json()["detail"]


def test_watch_pool_add_requires_invalid_condition(client):
    payload = _watch_payload()
    payload.pop("invalid_condition")
    response = client.post("/api/h5/watch-pool", json=payload)
    assert response.status_code == 400
    assert "invalid_condition" in response.json()["detail"]


def test_watch_pool_add_with_trading_system_instance_params(client, db_session):
    SeedService(db_session).init_defaults()
    payload = {
        "stock_code": "688001.SH",
        "stock_name": "Platform Test",
        "trading_system_code": "breakout",
        "entry_reason": "platform retest",
        "system_params_json": {
            "platform_upper_price": 20.5,
            "platform_support_price": 19.2,
            "key_observe_price": 20.8,
            "invalid_condition": "close below platform support",
        },
    }
    response = client.post("/api/h5/watch-pool", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["trading_system"] == "breakout"
    assert data["trading_system_code"] == "breakout"
    assert data["trading_system_name"] == "突破"
    assert data["system_stage"] == "observe"
    assert "platform_upper_price" not in data["system_params_json"]
    assert data["system_params_json"]["platform_support_price"] == 19.2
    assert data["system_params_json"]["key_observe_price"] == 20.8
    assert data["key_observe_price"] == 20.8
    assert data["invalid_condition"] == ""


def test_watch_pool_update_accepts_trading_system_instance_params(client, db_session):
    SeedService(db_session).init_defaults()
    created = client.post("/api/h5/watch-pool", json={
        "stock_code": "688011.SH",
        "stock_name": "Dynamic Param Test",
        "trading_system_code": "breakout",
        "entry_reason": "platform retest",
        "system_params_json": {
            "platform_upper_price": 20.5,
            "platform_support_price": 19.2,
            "key_observe_price": 20.8,
            "invalid_condition": "close below platform support",
        },
    })
    assert created.status_code == 200
    watch_id = created.json()["data"]["watch_id"]

    updated = client.put(f"/api/h5/watch-pool/{watch_id}", json={
        "trading_system_code": "breakout",
        "trading_system": "breakout",
        "entry_reason": "adjust platform params",
        "system_params_json": {
            "platform_upper_price": 21.5,
            "platform_support_price": 20.2,
            "key_observe_price": 21.8,
            "auto_remove_price": 19.9,
            "invalid_condition": "close below updated support",
        },
        "key_observe_price": 21.8,
        "auto_remove_price": 19.9,
        "invalid_condition": "close below updated support",
        "risk_tags": ["break_support"],
        "user_remark": "updated from detail drawer",
        "adjust_reason": "raise platform box",
    })

    assert updated.status_code == 200
    data = updated.json()["data"]
    assert data["trading_system_code"] == "breakout"
    assert "platform_upper_price" not in data["system_params_json"]
    assert data["system_params_json"]["platform_support_price"] == 20.2
    assert data["system_params_json"]["key_observe_price"] == 21.8
    assert data["system_params_json"]["auto_remove_price"] == 19.9
    assert data["key_observe_price"] == 21.8
    assert data["auto_remove_price"] == 19.9
    assert data["invalid_condition"] == "close below updated support"
    assert data["risk_tags"] == ["break_support"]
    assert data["user_remark"] == "updated from detail drawer"


def test_uptrend_watch_ignores_fixed_auto_remove_price(client, db_session):
    SeedService(db_session).init_defaults()

    created = client.post("/api/h5/watch-pool", json={
        "stock_code": "688019.SH",
        "stock_name": "Uptrend Remove Rule Test",
        "trading_system_code": "uptrend",
        "entry_reason": "trend pullback",
        "system_params_json": {"auto_remove_price": 18.5},
        "auto_remove_price": 18.5,
    })

    assert created.status_code == 200
    data = created.json()["data"]
    assert data["trading_system_code"] == "uptrend"
    assert data["auto_remove_price"] is None
    assert "auto_remove_price" not in data["system_params_json"]


def test_h5_signal_and_trade_return_rule_display_fields(client, db_session):
    SeedService(db_session).init_defaults()
    watch = WatchPool(
        stock_code="688012.SH",
        stock_name="Rule Display Test",
        active=True,
        status="trading",
        trading_system="breakout",
        trading_system_code="breakout",
    )
    db_session.add(watch)
    db_session.flush()
    signal = WatchSignal(
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        signal_type="buy",
        buy_point_type="b5_divergence",
        trading_system="breakout",
        trading_system_code="breakout",
        rule_code="b5_divergence",
        rule_type="buy_signal",
        strategy_name="rule_executor:macd_bottom_divergence",
        trigger_date=date(2026, 5, 5),
        trigger_time=datetime(2026, 5, 5, 10, 30),
        signal_status="buy_pending_confirm",
    )
    db_session.add(signal)
    db_session.flush()
    trade = WatchTrade(
        signal_id=signal.signal_id,
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        trading_system="breakout",
        trading_system_code="breakout",
        entry_rule_code="b5_divergence",
        active_sell_rule_codes_json=["m5_top_divergence", "m30_dead_cross"],
        active_stop_rule_codes_json=["break_platform_support"],
        trade_status="open",
    )
    db_session.add(trade)
    db_session.commit()

    signal_payload = client.get("/api/h5/watch-signals/recent").json()["data"][0]
    assert signal_payload["rule_name"] == "5分钟底背离"
    assert signal_payload["rule_timeframe"] == "5m"
    assert signal_payload["trading_system_name"] == "突破"
    assert signal_payload["rule_display_name"] == "5分钟底背离"

    trade_payload = client.get("/api/h5/watch-trades/recent").json()["data"][0]
    assert trade_payload["entry_rule_display_name"] == "5分钟底背离"
    assert trade_payload["trading_system_name"] == "突破"
    assert [item["display_name"] for item in trade_payload["active_sell_rules"]] == ["5分钟顶背离", "30分钟死叉"]
    assert [item["display_name"] for item in trade_payload["active_stop_rules"]] == ["收破支撑位"]


def test_watch_pool_add_with_system_code_requires_defined_params(client, db_session):
    SeedService(db_session).init_defaults()
    response = client.post("/api/h5/watch-pool", json={
        "stock_code": "688002.SH",
        "stock_name": "Missing Params",
        "trading_system_code": "breakout",
        "entry_reason": "platform retest",
        "system_params_json": {
            "platform_upper_price": 20.5,
            "key_observe_price": 20.8,
            "invalid_condition": "close below platform support",
        },
    })
    assert response.status_code == 400
    assert "platform_support_price" in response.json()["detail"]


def test_watch_pool_duplicate_add_updates_existing_row(db_session):
    service = PrdWatchPoolService(db_session)
    first = service.add_watch(_watch_payload(stock_name="First"))
    second = service.add_watch(_watch_payload(stock_name="Second", entry_reason="updated reason"))
    assert first.id == second.id
    assert db_session.query(WatchPool).filter(WatchPool.stock_code == "sh603019").count() == 1
    assert second.stock_name == "Second"
    assert second.entry_reason == "updated reason"


def test_watch_pool_mark_invalid_writes_status_log(db_session):
    service = PrdWatchPoolService(db_session)
    watch = service.add_watch(_watch_payload(stock_code="000001.SZ"))
    invalid = service.mark_invalid(watch.id, {"invalid_reason": "setup failed"})
    assert invalid.status == "invalid"
    assert invalid.status == "invalid"

    log = (
        db_session.query(WatchPoolStatusLog)
        .filter(WatchPoolStatusLog.watch_id == watch.id)
        .order_by(WatchPoolStatusLog.id.desc())
        .first()
    )
    assert log.operation_type == "mark_invalid"
    assert log.snapshot["invalid_reason"] == "setup failed"


def test_watch_pool_blacklist_requires_explicit_confirmation(db_session):
    service = PrdWatchPoolService(db_session)
    watch = service.add_watch(_watch_payload(stock_code="000002.SZ"))
    service.blacklist_watch(watch.id, "risk blacklist")

    with pytest.raises(ValueError, match="blacklist confirmation required"):
        service.add_watch(_watch_payload(stock_code="000002.SZ"))

    restored = service.add_watch(_watch_payload(stock_code="000002.SZ", confirm_blacklist_risk=True))
    assert restored.id == watch.id
    assert restored.status == "watching"
    assert restored.active is True


def test_h5_signal_confirm_buy_creates_watch_trade_and_execution(client, db_session):
    watch = WatchPool(stock_code="603019.SH", stock_name="中科曙光", reason="用户手动加入", status="watching", monitor_enabled=True, active=True)
    db_session.add(watch)
    db_session.flush()
    watch.status = "buy_pending_confirm"
    watch.status = "buy_pending_confirm"
    signal = WatchSignal(
        watch_id=watch.id,
        stock_code="603019.SH",
        stock_name="中科曙光",
        signal_type="buy",
        buy_point_type="B15 底背离买点",
        strategy_name="B15",
        signal_level="A",
        trigger_date=date(2026, 5, 5),
        trigger_time=datetime(2026, 5, 5, 10, 30),
        trigger_price=50.0,
        trigger_reason="买入观察信号，仅作为交易辅助，请结合个人交易规则确认。",
        signal_status="buy_pending_confirm",
        raw_snapshot={"source": "test"},
    )
    db_session.add(signal)
    db_session.commit()

    response = client.post(
        f"/api/h5/watch-signals/{signal.signal_id}/confirm-buy",
        json={"buy_price": 50.0, "amount": 100, "position_ratio": 0.1, "stop_loss_price": 48.0, "buy_point_confirmed": True},
    )
    assert response.status_code == 200
    trade_id = response.json()["data"]["trade_id"]

    repeat = client.post(f"/api/h5/watch-signals/{signal.signal_id}/confirm-buy", json={"buy_price": 50.0, "amount": 100, "stop_loss_price": 48.0, "buy_point_confirmed": True})
    assert repeat.status_code == 200
    assert repeat.json()["data"]["trade_id"] == trade_id

    executions = client.get(f"/api/h5/watch-trades/{trade_id}/executions")
    assert executions.status_code == 200
    assert executions.json()["data"][0]["execution_type"] == "buy"


def test_h5_confirm_sell_generates_trade_review(client, db_session):
    watch = WatchPool(stock_code="603019.SH", stock_name="中科曙光", reason="用户手动加入", status="watching", monitor_enabled=True, active=True)
    db_session.add(watch)
    db_session.flush()
    watch.status = "buy_pending_confirm"
    watch.status = "buy_pending_confirm"
    signal = WatchSignal(
        watch_id=watch.id,
        stock_code="603019.SH",
        stock_name="中科曙光",
        signal_type="buy",
        buy_point_type="支撑买点",
        strategy_name="support",
        signal_level="A",
        trigger_date=date(2026, 5, 5),
        trigger_time=datetime(2026, 5, 5, 10, 30),
    )
    signal.signal_status = "buy_pending_confirm"
    db_session.add(signal)
    db_session.commit()
    trade = client.post(f"/api/h5/watch-signals/{signal.signal_id}/confirm-buy", json={"buy_price": 10.0, "amount": 100, "stop_loss_price": 9.5, "buy_point_confirmed": True}).json()["data"]

    response = client.post(
        f"/api/h5/watch-trades/{trade['trade_id']}/confirm-sell",
        json={"sell_price": 11.0, "amount": 100, "execution_type": "sell", "is_full_exit": True},
    )
    assert response.status_code == 200
    assert response.json()["data"]["is_full_exit"] is True

    reviews = client.get("/api/h5/reviews/trade")
    assert reviews.status_code == 200
    assert reviews.json()["data"][0]["trade_id"] == trade["trade_id"]


def test_watch_pool_filters_update_invalid_and_signal_abandon(client, db_session):
    service = PrdWatchPoolService(db_session)
    watch = service.add_watch(_watch_payload(stock_code="000001.SZ", trading_system="breakout", stock_name="Ping An"))

    filtered = client.get("/api/h5/watch-pool", params={"status": "watching", "trading_system": "breakout", "keyword": "Ping"})
    assert filtered.status_code == 200
    assert filtered.json()["data"][0]["watch_id"] == watch.id

    missing_reason = client.put(f"/api/h5/watch-pool/{watch.id}", json={"key_observe_price": 12.3})
    assert missing_reason.status_code == 400

    updated = client.put(f"/api/h5/watch-pool/{watch.id}", json={"key_observe_price": 12.3, "adjust_reason": "tighten observe price"})
    assert updated.status_code == 200
    assert updated.json()["data"]["key_observe_price"] == 12.3

    signal = WatchSignal(
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        signal_type="buy",
        buy_point_type="platform_breakout_confirm",
        strategy_name="breakout",
        trigger_date=date(2026, 5, 5),
        trigger_time=datetime(2026, 5, 5, 10, 30),
        signal_status="buy_pending_confirm",
    )
    db_session.add(signal)
    db_session.commit()

    abandoned = client.post(f"/api/h5/watch-signals/{signal.signal_id}/abandon", json={"reason": "price moved away"})
    assert abandoned.status_code == 200
    assert abandoned.json()["data"]["abandoned_flag"] is True
    restored_watch = db_session.get(WatchPool, watch.id)
    assert restored_watch.status == "watching"
    assert restored_watch.system_stage == "observe"
    assert restored_watch.monitor_enabled is True
    assert restored_watch.signal_enabled is True

    invalid = client.post(f"/api/h5/watch-pool/{watch.id}/invalid", json={"invalid_reason": "setup failed"})
    assert invalid.status_code == 200
    assert invalid.json()["data"]["status"] == "invalid"


def test_confirm_buy_requires_pending_confirm_and_buy_point_and_stop_loss(client, db_session):
    watch = WatchPool(stock_code="000001.SZ", stock_name="Ping An", status="watching", monitor_enabled=True, active=True)
    db_session.add(watch)
    db_session.flush()
    signal = WatchSignal(
        watch_id=watch.id,
        stock_code=watch.stock_code,
        stock_name=watch.stock_name,
        signal_type="buy",
        buy_point_type="support_buy",
        strategy_name="support",
        trigger_date=date(2026, 5, 5),
        trigger_time=datetime(2026, 5, 5, 10, 30),
        signal_status="pending",
    )
    db_session.add(signal)
    db_session.commit()

    wrong_status = client.post(f"/api/h5/watch-signals/{signal.signal_id}/confirm-buy", json={"buy_price": 10, "amount": 100, "stop_loss_price": 9, "buy_point_confirmed": True})
    assert wrong_status.status_code == 400

    signal.signal_status = "buy_pending_confirm"
    db_session.commit()
    no_confirm = client.post(f"/api/h5/watch-signals/{signal.signal_id}/confirm-buy", json={"buy_price": 10, "amount": 100, "stop_loss_price": 9})
    assert no_confirm.status_code == 400

    no_stop = client.post(f"/api/h5/watch-signals/{signal.signal_id}/confirm-buy", json={"buy_price": 10, "amount": 100, "buy_point_confirmed": True})
    assert no_stop.status_code == 400


def test_confirm_sell_rejects_partial_exit(client, db_session):
    watch = WatchPool(stock_code="000001.SZ", stock_name="Ping An", status="trading", monitor_enabled=False, active=True)
    trade = WatchTrade(watch_id=1, stock_code="000001.SZ", stock_name="Ping An", first_buy_price=10, average_buy_price=10, total_buy_amount=100, remaining_amount=100, trade_status="open")
    db_session.add(watch)
    db_session.flush()
    trade.watch_id = watch.id
    db_session.add(trade)
    db_session.commit()

    response = client.post(f"/api/h5/watch-trades/{trade.id}/confirm-sell", json={"sell_price": 11, "amount": 50, "execution_type": "sell"})
    assert response.status_code == 400


def test_h5_reviews_are_exposed_by_period(client, db_session):
    db_session.add(ReviewForm(review_type="weekly", review_period="2026-W18", title="周复盘"))
    db_session.commit()
    response = client.get("/api/h5/reviews/weekly")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
