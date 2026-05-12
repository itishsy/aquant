from datetime import date, datetime

from app.models import MktHotStock, MktLimitUpPlate, MktLimitUpStock, ReviewForm, WatchPool, WatchSignal


def test_common_xueqiu_url_enveloped(client):
    response = client.get("/api/common/stocks/603019.SH/xueqiu-url")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["code"] == "SUCCESS"
    assert payload["data"]["xueqiu_url"] == "https://xueqiu.com/S/SH603019"


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


def test_h5_signal_confirm_buy_creates_watch_trade_and_execution(client, db_session):
    watch = WatchPool(stock_code="603019.SH", stock_name="中科曙光", reason="用户手动加入", pool_status="watching", monitor_enabled=True, active=True)
    db_session.add(watch)
    db_session.flush()
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
        raw_snapshot={"source": "test"},
    )
    db_session.add(signal)
    db_session.commit()

    response = client.post(
        f"/api/h5/watch-signals/{signal.signal_id}/confirm-buy",
        json={"buy_price": 50.0, "amount": 100, "position_ratio": 0.1, "stop_loss_price": 48.0},
    )
    assert response.status_code == 200
    trade_id = response.json()["data"]["trade_id"]

    repeat = client.post(f"/api/h5/watch-signals/{signal.signal_id}/confirm-buy", json={"buy_price": 50.0, "amount": 100})
    assert repeat.status_code == 200
    assert repeat.json()["data"]["trade_id"] == trade_id

    executions = client.get(f"/api/h5/watch-trades/{trade_id}/executions")
    assert executions.status_code == 200
    assert executions.json()["data"][0]["execution_type"] == "buy"


def test_h5_confirm_sell_generates_trade_review(client, db_session):
    watch = WatchPool(stock_code="603019.SH", stock_name="中科曙光", reason="用户手动加入", pool_status="watching", monitor_enabled=True, active=True)
    db_session.add(watch)
    db_session.flush()
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
    db_session.add(signal)
    db_session.commit()
    trade = client.post(f"/api/h5/watch-signals/{signal.signal_id}/confirm-buy", json={"buy_price": 10.0, "amount": 100}).json()["data"]

    response = client.post(
        f"/api/h5/watch-trades/{trade['trade_id']}/confirm-sell",
        json={"sell_price": 11.0, "amount": 100, "execution_type": "sell", "is_full_exit": True},
    )
    assert response.status_code == 200
    assert response.json()["data"]["is_full_exit"] is True

    reviews = client.get("/api/h5/reviews/trade")
    assert reviews.status_code == 200
    assert reviews.json()["data"][0]["trade_id"] == trade["trade_id"]


def test_h5_reviews_are_exposed_by_period(client, db_session):
    db_session.add(ReviewForm(review_type="weekly", review_period="2026-W18", title="周复盘"))
    db_session.commit()
    response = client.get("/api/h5/reviews/weekly")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
