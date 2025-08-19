from fastapi.testclient import TestClient
from mcp_server.main import app
from datetime import datetime, timedelta

client = TestClient(app)
api_key = "your-secret-api-key"
headers = {"X-API-Key": api_key}

def test_get_bars_success():
    start = datetime.now() - timedelta(days=1)
    end = datetime.now()
    response = client.post(
        "/tool/market_data.get_bars",
        json={
            "symbol": "EUR.USD",
            "asset_type": "FX",
            "tf": "1m",
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "EUR.USD"
    assert data["tf"] == "1m"
    assert len(data["bars"]) > 0

def test_get_bars_invalid_symbol():
    start = datetime.now() - timedelta(days=1)
    end = datetime.now()
    response = client.post(
        "/tool/market_data.get_bars",
        json={
            "asset_type": "FX",
            "tf": "1m",
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 422

def test_get_bars_invalid_date_range():
    start = datetime.now()
    end = datetime.now() - timedelta(days=1)
    response = client.post(
        "/tool/market_data.get_bars",
        json={
            "symbol": "EUR.USD",
            "asset_type": "FX",
            "tf": "1m",
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 400
