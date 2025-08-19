from fastapi.testclient import TestClient
from mcp_server.main import app

client = TestClient(app)
api_key = "your-secret-api-key"
headers = {"X-API-Key": api_key}

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
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "test-plan-1"
    assert data["status"] == "ACCEPTED"
    assert data["dry_run"] is True

def test_place_bracket_idempotency():
    payload = {
        "plan_id": "test-plan-idempotency",
        "account": "DU12345",
        "symbol": "MES",
        "asset_type": "FUT",
        "qty": 1,
        "side": "BUY",
        "entry": {"type": "LMT", "price": 5550.25},
        "stop": {"type": "STP", "stop_price": 5538.25},
        "take": {"type": "LMT", "price": 5563.25},
        "tif": "DAY",
    }
    response1 = client.post("/tool/orders.place_bracket", json=payload, headers=headers)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["status"] == "ACCEPTED"

    response2 = client.post("/tool/orders.place_bracket", json=payload, headers=headers)
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["status"] == "DUPLICATE"
    assert data1["parent_id"] == data2["parent_id"]


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
        headers=headers,
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
        headers=headers,
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
        headers=headers,
    )
    assert response.status_code == 409
