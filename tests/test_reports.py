
from fastapi.testclient import TestClient
from datetime import datetime
from app.models import LedgerTransaction

def test_reports_flow(client: TestClient, db_session):
    # 1. Register User (user: "reportuser")
    login_data = {"username": "reportuser", "password": "password123"}
    resp = client.post("/api/auth/register", json=login_data)
    assert resp.status_code == 200
    token = client.post("/api/auth/login", json=login_data).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Categories (Ensure Groceries exists)
    cats = client.get("/api/categories", headers=headers).json()
    groceries = next(c for c in cats if c["name"] == "Groceries")
    
    # 3. Create Transactions for May 2024
    # Transaction 1: $100 Groceries
    client.post("/api/transactions", json={
        "category_id": groceries["id"],
        "amount": 100.0,
        "description": "Weekly Shop",
        "type": "DEBIT",
        "occurred_on": "2024-05-15T12:00:00"
    }, headers=headers)

    # Transaction 2: $50 Groceries
    client.post("/api/transactions", json={
        "category_id": groceries["id"],
        "amount": 50.0,
        "description": "Snacks",
        "type": "DEBIT",
        "occurred_on": "2024-05-20T12:00:00"
    }, headers=headers)
    
    # Transaction 3: $20 Utilities (Create Category first?)
    # For MVP we only have default categories. Assuming Utilities exists or we use Groceries.
    # Let's create 'Utilities' via API? No, create_category API exists.
    cat_resp = client.post("/api/categories", json={"name": "Utilities"}, headers=headers)
    assert cat_resp.status_code == 201
    utils_id = cat_resp.json()["id"]

    client.post("/api/transactions", json={
        "category_id": utils_id,
        "amount": 200.0,
        "description": "Electric Bill",
        "type": "DEBIT",
        "occurred_on": "2024-05-25T12:00:00"
    }, headers=headers)

    # 4. Create Transaction for DIFFERENT Month (June) - Should ensure filter works
    client.post("/api/transactions", json={
        "category_id": groceries["id"],
        "amount": 999.0,
        "description": "June Shop",
        "type": "DEBIT",
        "occurred_on": "2024-06-01T12:00:00"
    }, headers=headers)

    # 5. GET /reports/monthly-category?year=2024&month=5
    resp = client.get("/api/reports/monthly-category?year=2024&month=5", headers=headers)
    assert resp.status_code == 200
    report = resp.json()
    
    # Expect: Groceries: 150 (100+50), Utilities: 200
    g_row = next(r for r in report if r["category"] == "Groceries")
    u_row = next(r for r in report if r["category"] == "Utilities")
    
    assert g_row["amount"] == 150.0
    assert u_row["amount"] == 200.0
    
    # Ensure 999 is not there
    total = sum(r["amount"] for r in report)
    assert total == 350.0

    # 6. GET /reports/monthly-summary?year=2024&month=5
    resp = client.get("/api/reports/monthly-summary?year=2024&month=5", headers=headers)
    assert resp.status_code == 200
    summary = resp.json()
    
    assert summary["expenses"] == 350.0
    assert summary["income"] == 0.0 # No income yet
    assert summary["net"] == -350.0
