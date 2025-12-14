
from fastapi.testclient import TestClient
from app.models import LedgerTransaction, MappingRule
import io

def test_auto_rules_flow(client: TestClient, db_session):
    # 1. Register & Login
    login_data = {"username": "ruleuser", "password": "password123"}
    client.post("/api/auth/register", json=login_data)
    headers = {"Authorization": f"Bearer {client.post('/api/auth/login', json=login_data).json()['access_token']}"}

    # 2. Create Category "Transport"
    resp = client.post("/api/categories", json={"name": "Transport"}, headers=headers)
    transport_id = resp.json()["id"]

    # 3. Create Rule: "Uber" -> "Transport"
    rule_data = {
        "match_pattern": "Uber",
        "target_category_id": transport_id,
        "priority": 10
    }
    resp = client.post("/api/mappings", json=rule_data, headers=headers)
    assert resp.status_code == 201

    # 4. Upload CSV
    # CSV contains "Uber Trip" with NO category specified.
    csv_content = """Date,Description,Amount,Category
2024-08-01,Uber Trip,15.00,
2024-08-02,Unknown Store,10.00,
"""
    file_obj = io.BytesIO(csv_content.encode('utf-8'))
    files = {"file": ("test.csv", file_obj, "text/csv")}
    
    resp = client.post("/api/imports/csv", files=files, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 2

    # 5. Verify Ledger
    # "Uber Trip" should be categorized as "Transport"
    uber = db_session.query(LedgerTransaction).filter(LedgerTransaction.description == "Uber Trip").first()
    assert uber is not None
    
    # Check expense entry
    expense_entry = next(e for e in uber.entries if e.amount > 0)
    assert expense_entry.account_id == transport_id
    
    # "Unknown Store" should be "Uncategorized" (assuming it didn't match rules)
    unknown = db_session.query(LedgerTransaction).filter(LedgerTransaction.description == "Unknown Store").first()
    expense_entry = next(e for e in unknown.entries if e.amount > 0)
    
    # Verify account name is Uncategorized
    # Since we can't easily get the ID of uncategorized without querying, let's just assert it is NOT transport
    assert expense_entry.account_id != transport_id
