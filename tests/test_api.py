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
