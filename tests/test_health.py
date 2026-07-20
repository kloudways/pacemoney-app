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


def test_summary_empty_db():
    response = client.get("/transactions/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["by_category"] == {}


def test_create_and_list_transaction():
    payload = {"amount": 49.99, "description": "Grocery run", "category": "food"}
    create = client.post("/transactions", json=payload)
    assert create.status_code == 201
    data = create.json()
    assert data["amount"] == 49.99
    assert data["category"] == "food"
    assert "id" in data

    listed = client.get("/transactions").json()
    assert len(listed) == 1


def test_get_transaction_by_id():
    payload = {"amount": 12.50, "description": "Bus fare", "category": "transport"}
    created = client.post("/transactions", json=payload).json()
    response = client.get(f"/transactions/{created['id']}")
    assert response.status_code == 200
    assert response.json()["description"] == "Bus fare"


def test_get_transaction_not_found():
    response = client.get("/transactions/999999")
    assert response.status_code == 404


def test_delete_transaction():
    created = client.post("/transactions", json={"amount": 5.0, "description": "Coffee", "category": "food"}).json()
    delete = client.delete(f"/transactions/{created['id']}")
    assert delete.status_code == 204
    assert client.get(f"/transactions/{created['id']}").status_code == 404


def test_delete_transaction_not_found():
    response = client.delete("/transactions/999999")
    assert response.status_code == 404


def test_create_transaction_missing_fields():
    response = client.post("/transactions", json={"amount": 10.0})
    assert response.status_code == 422


def test_create_transaction_negative_amount():
    response = client.post("/transactions", json={"amount": -5.0, "description": "Bad", "category": "food"})
    assert response.status_code == 422


def test_create_transaction_zero_amount():
    response = client.post("/transactions", json={"amount": 0.0, "description": "Zero", "category": "food"})
    assert response.status_code == 422


def test_get_transaction_invalid_id_type():
    response = client.get("/transactions/notanumber")
    assert response.status_code == 422


def test_summary_reflects_created_transactions():
    r1 = client.post("/transactions", json={"amount": 100.00, "description": "Rent", "category": "housing_v2"})
    r2 = client.post("/transactions", json={"amount": 30.00, "description": "Lunch", "category": "food_v2"})
    r3 = client.post("/transactions", json={"amount": 20.00, "description": "Dinner", "category": "food_v2"})

    data = client.get("/transactions/summary").json()
    assert data["by_category"]["housing_v2"] == 100.0
    assert data["by_category"]["food_v2"] == 50.0

    for r in [r1, r2, r3]:
        client.delete(f"/transactions/{r.json()['id']}")


def test_security_headers_present():
    response = client.get("/health")
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert "content-security-policy" in response.headers
