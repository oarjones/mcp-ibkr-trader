from fastapi.testclient import TestClient
from mcp_server.main import app, API_KEY, API_KEY_NAME

client = TestClient(app)
headers = {"X-API-Key": API_KEY} if API_KEY else {}

def test_api_key_missing():
    if not API_KEY:
        return
    response = client.post("/tool/portfolio.get_positions")
    assert response.status_code == 401

def test_api_key_invalid():
    if not API_KEY:
        return
    response = client.post(
        "/tool/portfolio.get_positions", headers={"X-API-Key": "invalid-key"}
    )
    assert response.status_code == 401

def test_api_key_valid():
    if not API_KEY:
        return
    response = client.post(
        "/tool/portfolio.get_positions", headers=headers
    )
    assert response.status_code == 200

def test_correlation_id_echo():
    correlation_id = "test-correlation-id"
    local_headers = headers.copy()
    local_headers["X-Correlation-ID"] = correlation_id
    response = client.get("/health", headers=local_headers)
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == correlation_id