
from fastapi.testclient import TestClient
from app.models import LedgerTransaction

def test_share_methods(client: TestClient, db_session):
    # 1. Register & Login
    login_data = {"username": "sharemethoduser", "password": "password123"}
    client.post("/api/auth/register", json=login_data)
    headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json=login_data).json()['access_token']}"}

    # 2. Create Category
    resp = client.post("/api/categories", json={"name": "Vacation"}, headers=headers)
    cat_id = resp.json()["id"]

    # Test A: Percentage (I pay 40% of 200) -> 80 Expense, 120 Reimbursable
    txn_data = {
        "category_id": cat_id,
        "description": "Hotel",
        "amount": 200.00,
        "type": "DEBIT",
        "occurred_on": "2024-10-01T12:00:00",
        "share": {
            "method": "PERCENTAGE",
            "value": 40.0
        }
    }
    resp = client.post("/api/transactions", json=txn_data, headers=headers)
    assert resp.status_code == 201
    
    txn = db_session.query(LedgerTransaction).filter(LedgerTransaction.description == "Hotel").first()
    expense = next(e for e in txn.entries if e.account_id == cat_id)
    reimb = next(e for e in txn.entries if e.account.name == "Reimbursable")
    
    assert expense.amount == 80.0
    assert reimb.amount == 120.0

    # Test B: Equal Split (3 people, Total 300) -> 100 Expense, 200 Reimbursable
    txn_data = {
        "category_id": cat_id,
        "description": "Group Dinner",
        "amount": 300.00,
        "type": "DEBIT",
        "occurred_on": "2024-10-02T12:00:00",
        "share": {
            "method": "EQUAL",
            "value": 3
        }
    }
    resp = client.post("/api/transactions", json=txn_data, headers=headers)
    assert resp.status_code == 201

    txn = db_session.query(LedgerTransaction).filter(LedgerTransaction.description == "Group Dinner").first()
    expense = next(e for e in txn.entries if e.account_id == cat_id)
    reimb = next(e for e in txn.entries if e.account.name == "Reimbursable")
    
    assert expense.amount == 100.0
    assert reimb.amount == 200.0
