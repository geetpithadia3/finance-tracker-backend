
from fastapi.testclient import TestClient
from app.models import LedgerTransaction
import io

def test_csv_import_flow(client: TestClient, db_session):
    # 1. Register User which creates Party and Accounts (Groceries)
    login_data = {"username": "importuser", "password": "password123"}
    resp = client.post("/api/auth/register", json=login_data)
    assert resp.status_code == 200
    
    # Login
    resp = client.post("/api/auth/login", json=login_data)
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Prepare CSV (Assume Groceries account exists)
    csv_content = """Date,Description,Amount,Category
2024-06-01,Whole Foods,150.00,Groceries
2024-06-02,Uber Trip,-25.50,Transport
2024-06-03,Unknown store,10.00,
"""
    # Note: Uber Trip is negative, our parser takes absolute value. 
    # Empty category should map to "Uncategorized"
    
    file_obj = io.BytesIO(csv_content.encode('utf-8'))
    
    # 3. POST /imports/csv
    files = {"file": ("test.csv", file_obj, "text/csv")}
    resp = client.post("/api/imports/csv", files=files, headers=headers)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 3
    assert data["skipped"] == 0
    
    # 4. Verify Database
    txns = db_session.query(LedgerTransaction).all()
    # 1 from Groceries, 1 from Transport (Transport might not exist -> Uncategorized? No, code creates it or maps to uncategorized if logic fails, let's check code)
    # The code maps "Transport" to existing account or Uncategorized?
    # Code: target_account_id = account_map.get(cat_name, uncategorized_id)
    # "Transport" does not exist in seed, so it should go to Uncategorized.
    
    # "Groceries" exists in seed.
    whole_foods = next(t for t in txns if t.description == "Whole Foods")
    assert whole_foods is not None
    
    # Check entries for Whole Foods
    # Debits positive 150 to Groceries
    expenses_entry = next(e for e in whole_foods.entries if e.amount > 0)
    assert expenses_entry.amount == 150.0
    
    unknown = next(t for t in txns if t.description == "Unknown store")
    assert unknown is not None
    # Should be uncategorized
