
from fastapi.testclient import TestClient
from app.models import LedgerTransaction

def test_transfer_flow(client: TestClient, db_session):
    # 1. Register & Login
    login_data = {"username": "transferuser", "password": "password123"}
    resp = client.post("/api/auth/register", json=login_data)
    headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json=login_data).json()['access_token']}"}

    # 2. Setup Accounts
    # Checking (Source - ASSET)
    resp = client.post("/api/accounts", json={"name": "Checking", "type": "ASSET"}, headers=headers)
    assert resp.status_code == 201
    checking_id = resp.json()["id"]

    # Savings (Destination - ASSET)
    resp = client.post("/api/accounts", json={"name": "Savings", "type": "ASSET"}, headers=headers)
    assert resp.status_code == 201
    savings_id = resp.json()["id"]

    # 3. Create Transfer (Checking -> Savings)
    # Note: category_id required by schema validation for now, can reuse savings_id
    txn_data = {
        "category_id": savings_id, # Placeholder
        "description": "Save for rainy day",
        "amount": 500.00,
        "type": "TRANSFER",
        "occurred_on": "2024-07-01T10:00:00",
        "source_account_id": checking_id,
        "destination_account_id": savings_id
    }
    
    resp = client.post("/api/transactions", json=txn_data, headers=headers)
    assert resp.status_code == 201
    
    # 4. Verify Ledger
    txn = db_session.query(LedgerTransaction).filter(LedgerTransaction.description == "Save for rainy day").first()
    assert txn is not None
    
    # Check Entries
    # Credit Checking (-500)
    # Debit Savings (+500)
    
    checking_entry = next(e for e in txn.entries if e.account_id == checking_id)
    savings_entry = next(e for e in txn.entries if e.account_id == savings_id)
    
    assert checking_entry.amount == -500.0
    assert savings_entry.amount == 500.0
    
def test_split_transaction_flow(client: TestClient, db_session):
    # 1. Register & Login (Reuse or new)
    login_data = {"username": "splituser", "password": "password123"}
    client.post("/api/auth/register", json=login_data)
    headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json=login_data).json()['access_token']}"}
    
    # 2. Setup Categories
    cat1 = client.post("/api/categories", json={"name": "Food"}, headers=headers).json()["id"]
    cat2 = client.post("/api/categories", json={"name": "Home"}, headers=headers).json()["id"]
    
    # 3. Create Split Transaction
    # Should create 2 separate transactions with different descriptions
    txn_data = {
        "category_id": cat1, # Not used for splits anymore
        "description": "Walmart Run", # Not used for splits anymore
        "amount": 100.00, # Not used for splits anymore
        "type": "DEBIT",
        "occurred_on": "2024-07-02T10:00:00",
        "splits": [
            {"category_id": cat1, "amount": 60.00, "description": "Groceries at Walmart"},
            {"category_id": cat2, "amount": 40.00, "description": "Home supplies at Walmart"}
        ]
    }
    
    resp = client.post("/api/transactions", json=txn_data, headers=headers)
    assert resp.status_code == 201
    
    # Should return list of 2 transactions
    transactions = resp.json()
    assert len(transactions) == 2
    assert transactions[0]["amount"] == 60.0
    assert transactions[1]["amount"] == 40.0
    
    # 4. Verify Ledger - Should have 2 separate LedgerTransactions
    txn1 = db_session.query(LedgerTransaction).filter(
        LedgerTransaction.description == "Groceries at Walmart"
    ).first()
    txn2 = db_session.query(LedgerTransaction).filter(
        LedgerTransaction.description == "Home supplies at Walmart"
    ).first()
    
    assert txn1 is not None
    assert txn2 is not None
    
    # Each transaction should have 2 entries (debit + credit)
    assert len(txn1.entries) == 2
    assert len(txn2.entries) == 2
    
    # Verify amounts
    cat1_entry = next(e for e in txn1.entries if e.account_id == cat1)
    assert cat1_entry.amount == 60.0
    
    cat2_entry = next(e for e in txn2.entries if e.account_id == cat2)
    assert cat2_entry.amount == 40.0
