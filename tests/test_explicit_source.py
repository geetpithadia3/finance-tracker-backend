
from fastapi.testclient import TestClient
from app.models import LedgerTransaction

def test_explicit_source_flow(client: TestClient, db_session):
    # 1. Register
    login_data = {"username": "sourceuser", "password": "password123"}
    resp = client.post("/api/auth/register", json=login_data)
    headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json=login_data).json()['access_token']}"}

    # 2. Create a "Chase Credit Card" (Liability)
    resp = client.post("/api/accounts", json={"name": "Chase Visa", "type": "LIABILITY"}, headers=headers)
    assert resp.status_code == 201
    cc_id = resp.json()["id"]

    # 3. Create a Category (Expense)
    resp = client.post("/api/categories", json={"name": "Tech"}, headers=headers)
    cat_id = resp.json()["id"]

    # 4. Create Transaction using Credit Card
    txn_data = {
        "category_id": cat_id,
        "amount": 2000.00,
        "description": "New Laptop",
        "type": "DEBIT",
        "occurred_on": "2024-06-15T12:00:00",
        "source_account_id": cc_id
    }
    resp = client.post("/api/transactions", json=txn_data, headers=headers)
    assert resp.status_code == 201
    
    # 5. Verify Database
    txn = db_session.query(LedgerTransaction).filter(LedgerTransaction.description == "New Laptop").first()
    assert txn is not None
    
    # Check entries
    # Should be: Credit Liability (-2000), Debit Expense (+2000)
    cc_entry = next(e for e in txn.entries if e.account_id == cc_id)
    exp_entry = next(e for e in txn.entries if e.account_id == cat_id)
    
    assert cc_entry.amount == -2000.0
    assert exp_entry.amount == 2000.0
