from fastapi.testclient import TestClient
from mcp_server.main import app

client = TestClient(app)

def test_place_bracket_success():
    response = client.post(
        "/tool/orders.place_bracket",
        json={
            "plan_id": "test-plan-1",
            "account": "DU12345",
            "symbol": "MES",
            "asset_type": "FUT",
            "qty": 1,
            "side": "BUY",
            "entry": {"type": "LMT", "price": 5550.25},
            "stop": {"type": "STP", "stop_price": 5538.25},
            "take": {"type": "LMT", "price": 5563.25},
            "tif": "DAY",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "test-plan-1"
    assert data["status"] == "ACCEPTED"
    assert data["dry_run"] is True

def test_place_bracket_invalid_qty():
    response = client.post(
        "/tool/orders.place_bracket",
        json={
            "plan_id": "test-plan-2",
            "account": "DU12345",
            "symbol": "MES",
            "asset_type": "FUT",
            "qty": 0,
            "side": "BUY",
            "entry": {"type": "LMT", "price": 5550.25},
            "stop": {"type": "STP", "stop_price": 5538.25},
            "take": {"type": "LMT", "price": 5563.25},
            "tif": "DAY",
        },
    )
    assert response.status_code == 422

def test_place_bracket_invalid_prices():
    response = client.post(
        "/tool/orders.place_bracket",
        json={
            "plan_id": "test-plan-3",
            "account": "DU12345",
            "symbol": "MES",
            "asset_type": "FUT",
            "qty": 1,
            "side": "BUY",
            "entry": {"type": "LMT", "price": 5550.25},
            "stop": {"type": "STP", "stop_price": 5560.25}, # stop > entry
            "take": {"type": "LMT", "price": 5563.25},
            "tif": "DAY",
        },
    )
    assert response.status_code == 400

def test_place_bracket_requires_approval():
    response = client.post(
        "/tool/orders.place_bracket",
        json={
            "plan_id": "test-plan-4",
            "account": "DU12345",
            "symbol": "MES",
            "asset_type": "FUT",
            "qty": 1,
            "side": "BUY",
            "entry": {"type": "LMT", "price": 5550.25},
            "stop": {"type": "STP", "stop_price": 5538.25},
            "take": {"type": "LMT", "price": 5563.25},
            "tif": "DAY",
            "requires_approval": True,
        },
    )
    assert response.status_code == 409
