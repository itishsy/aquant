from datetime import date


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_market_summary(client):
    client.get(f"/api/market/daily?trade_date={date(2026, 4, 24)}")
    response = client.get("/api/market/summary")
    assert response.status_code == 200
    assert "market_score" in response.json()


def test_limit_up_summary_reads_existing_without_recollect(client, db_session):
    from app.models import LimitUpDaily

    trade_date = date(2026, 4, 30)
    db_session.add(
        LimitUpDaily(
            trade_date=trade_date,
            stock_code="600000.SH",
            stock_name="浦发银行",
            limit_time="09:31",
            board_count=1,
            concept="测试",
        )
    )
    db_session.commit()

    response = client.get(f"/api/limit-up/summary?trade_date={trade_date}")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert db_session.query(LimitUpDaily).filter(LimitUpDaily.trade_date == trade_date).count() == 1
