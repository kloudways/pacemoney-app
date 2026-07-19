from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "pacemoney", "version": "2.0.0"}


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


def test_get_transaction_by_id():
    payload = {"amount": 12.50, "description": "Bus fare", "category": "transport"}
    created = client.post("/transactions", json=payload).json()
    response = client.get(f"/transactions/{created['id']}")
    assert response.status_code == 200
    assert response.json()["description"] == "Bus fare"


def test_get_transaction_not_found():
    response = client.get("/transactions/999999")
    assert response.status_code == 404


def test_summary_response_structure():
    response = client.get("/transactions/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "by_category" in data


def test_summary_reflects_created_transactions():
    r1 = client.post("/transactions", json={"amount": 100.00, "description": "Rent", "category": "housing_v2"})
    r2 = client.post("/transactions", json={"amount": 30.00, "description": "Lunch", "category": "food_v2"})
    r3 = client.post("/transactions", json={"amount": 20.00, "description": "Dinner", "category": "food_v2"})

    data = client.get("/transactions/summary").json()
    assert data["by_category"]["housing_v2"] == 100.0
    assert data["by_category"]["food_v2"] == 50.0

    for r in [r1, r2, r3]:
        client.delete(f"/transactions/{r.json()['id']}")
