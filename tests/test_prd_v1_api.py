from datetime import date, datetime

import pytest

from app.models import ConfigDictionary, MktHotStock, MktLimitUpPlate, MktLimitUpStock, ReviewForm, WatchPool, WatchPoolStatusLog, WatchSignal, WatchTrade
from app.services.prd_v1 import PrdWatchPoolService, SeedService


def test_common_xueqiu_url_enveloped(client):
    response = client.get("/api/common/stocks/603019.SH/xueqiu-url")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["code"] == "SUCCESS"
    assert payload["data"]["xueqiu_url"] == "https://xueqiu.com/S/SH603019"


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
        "platform_breakout": "平台突破",
        "uptrend": "上涨趋势",
        "relay": "追涨接力",
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


def test_h5_market_uses_raw_hot_stock_fields(client, db_session):
    trade_date = date(2026, 4, 24)
    db_session.add(
        MktHotStock(
            trade_date=trade_date,
            platform="mock",
            stock_code="603019.SH",
            stock_name="中科曙光",
            platform_rank=1,
            raw_score=98.0,
            raw_reason="平台原始原因",
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
    db_session.add_all(
        [
            MktLimitUpPlate(
                trade_date=trade_date,
                source="mock",
                platform="mock",
                plate_code="p1",
                plate_name="AI应用",
                limit_up_count=8,
                change_pct=2.5,
                up_reason="上榜理由来自涨停板块表",
            ),
            MktLimitUpPlate(
                trade_date=trade_date,
                source="mock",
                platform="mock",
                plate_code="p2",
                plate_name="ST板块",
                limit_up_count=99,
                change_pct=9.9,
                up_reason="应排除 ST",
            ),
        ]
    )
    db_session.commit()

    response = client.get(f"/api/h5/market/hot-stocks?trade_date={trade_date}&platform=mock")
    assert response.status_code == 200
    item = response.json()["data"]["list"][0]
    assert item["platform_rank"] == 1
    assert item["raw_score"] == 98.0
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
    assert boards[0]["limit_up_count"] == 8
    assert boards[0]["up_reason"] == "上榜理由来自涨停板块表"
    assert all("ST" not in item["board_name"] for item in boards)


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
        "source_platform": "mock",
        "source_rank": 1,
        "source_score": 98,
        "source_reason": "平台原始原因",
    }
    first = client.post("/api/h5/watch-pool", json=payload)
    second = client.post("/api/h5/watch-pool", json={**payload, "labels": ["趋势"]})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["watch_id"] == second.json()["data"]["watch_id"]
    assert second.json()["data"]["pool_status"] == "watching"
    assert second.json()["data"]["monitor_enabled"] is True


def _watch_payload(**overrides):
    payload = {
        "stock_code": "603019.SH",
        "stock_name": "Aquant Test",
        "trading_system": "uptrend",
        "entry_reason": "manual selected from hot list",
        "key_observe_price": 50.0,
        "invalid_condition": "close below 48",
        "source_type": "manual",
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


def test_watch_pool_duplicate_add_updates_existing_row(db_session):
    service = PrdWatchPoolService(db_session)
    first = service.add_watch(_watch_payload(stock_name="First"))
    second = service.add_watch(_watch_payload(stock_name="Second", entry_reason="updated reason"))
    assert first.id == second.id
    assert db_session.query(WatchPool).filter(WatchPool.stock_code == "603019.SH").count() == 1
    assert second.stock_name == "Second"
    assert second.entry_reason == "updated reason"


def test_watch_pool_mark_invalid_writes_status_log(db_session):
    service = PrdWatchPoolService(db_session)
    watch = service.add_watch(_watch_payload(stock_code="000001.SZ"))
    invalid = service.mark_invalid(watch.id, {"invalid_reason": "setup failed"})
    assert invalid.lifecycle_status == "invalid"
    assert invalid.pool_status == "invalid"

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
    assert restored.lifecycle_status == "watching"
    assert restored.pool_status == "watching"
    assert restored.is_blacklist is False


def test_h5_signal_confirm_buy_creates_watch_trade_and_execution(client, db_session):
    watch = WatchPool(stock_code="603019.SH", stock_name="中科曙光", reason="用户手动加入", pool_status="watching", monitor_enabled=True, active=True)
    db_session.add(watch)
    db_session.flush()
    watch.pool_status = "buy_pending_confirm"
    watch.lifecycle_status = "buy_pending_confirm"
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
    watch = WatchPool(stock_code="603019.SH", stock_name="中科曙光", reason="用户手动加入", pool_status="watching", monitor_enabled=True, active=True)
    db_session.add(watch)
    db_session.flush()
    watch.pool_status = "buy_pending_confirm"
    watch.lifecycle_status = "buy_pending_confirm"
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
    watch = service.add_watch(_watch_payload(stock_code="000001.SZ", trading_system="platform_breakout", stock_name="Ping An"))

    filtered = client.get("/api/h5/watch-pool", params={"lifecycle_status": "watching", "trading_system": "platform_breakout", "keyword": "Ping"})
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

    invalid = client.post(f"/api/h5/watch-pool/{watch.id}/invalid", json={"invalid_reason": "setup failed"})
    assert invalid.status_code == 200
    assert invalid.json()["data"]["lifecycle_status"] == "invalid"


def test_confirm_buy_requires_pending_confirm_and_buy_point_and_stop_loss(client, db_session):
    watch = WatchPool(stock_code="000001.SZ", stock_name="Ping An", pool_status="watching", lifecycle_status="watching", monitor_enabled=True, active=True)
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
    watch = WatchPool(stock_code="000001.SZ", stock_name="Ping An", pool_status="trading", lifecycle_status="trading", monitor_enabled=False, active=True)
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
