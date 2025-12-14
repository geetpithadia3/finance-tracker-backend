
from fastapi.testclient import TestClient
from app.models import LedgerTransaction

def test_personal_share_flow(client: TestClient, db_session):
    # 1. Register & Login
    login_data = {"username": "shareuser", "password": "password123"}
    client.post("/api/auth/register", json=login_data)
    headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json=login_data).json()['access_token']}"}

    # 2. Create Category "Dinner"
    resp = client.post("/api/categories", json={"name": "Dinner"}, headers=headers)
    cat_id = resp.json()["id"]

    # 3. Create Transaction with Personal Share
    # Total $100, My Share $40 (So $60 is reimbursable)
    txn_data = {
        "category_id": cat_id,
        "description": "Shared Dinner",
        "amount": 100.00,
        "type": "DEBIT",
        "occurred_on": "2024-09-01T20:00:00",
        "personal_amount": 40.00
    }
    
    resp = client.post("/api/transactions", json=txn_data, headers=headers)
    assert resp.status_code == 201
    
    # 4. Verify Ledger
    txn = db_session.query(LedgerTransaction).filter(LedgerTransaction.description == "Shared Dinner").first()
    assert txn is not None
    
    # Check entries
    # 1. Source Credit -100
    # 2. Expense Debit +40
    # 3. Reimbursable Debit +60
    
    assert len(txn.entries) == 3
    
    source_entry = next(e for e in txn.entries if e.amount == -100.0)
    personal_entry = next(e for e in txn.entries if e.account_id == cat_id)
    reimb_entry = next(e for e in txn.entries if e.account_id != cat_id and e.amount > 0 and e.amount != 40.0)
    
    assert personal_entry.amount == 40.0
    assert reimb_entry.amount == 60.0
    
    # Check account name of reimb entry
    assert reimb_entry.account.name == "Reimbursable"
    assert reimb_entry.account.type == "ASSET"
