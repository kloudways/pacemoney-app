from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "pacemoney"}


def test_metrics_endpoint_reachable():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_request_duration_seconds" in response.text


def test_list_transactions_empty_on_fresh_db():
    response = client.get("/transactions")
    assert response.status_code == 200
    assert response.json() == []


def test_create_and_list_transaction():
    payload = {"amount": 49.99, "description": "Grocery run", "category": "food"}
    create = client.post("/transactions", json=payload)
    assert create.status_code == 201
    data = create.json()
    assert data["amount"] == 49.99
    assert data["category"] == "food"
    assert "id" in data
