import pytest
from datetime import datetime
from app.services.ledger_service import LedgerService
from app.models import Entry

def test_ledger_double_entry(db_session):
    service = LedgerService(db_session)
    
    # 1. Create Party and Accounts
    party = service.create_party("USER", "TestUser")
    cash = service.create_account(party.id, "Cash", "ASSET")
    groceries = service.create_account(party.id, "Groceries", "EXPENSE")
    
    # 2. Record Transaction ($50 Groceries paid by Cash)
    entries = [
        {"account_id": cash.id, "amount": -50.0},
        {"account_id": groceries.id, "amount": 50.0}
    ]
    txn = service.record_transaction(party.id, "Weekly Groceries", datetime.now(), entries)
    
    # 3. Verify
    assert txn.description == "Weekly Groceries"
    
    # Verify entries exist
    saved_entries = db_session.query(Entry).filter(Entry.transaction_id == txn.id).all()
    assert len(saved_entries) == 2
    
    # Verify Sum is Zero
    total = sum(e.amount for e in saved_entries)
    assert abs(total) < 0.0001
    
    # 4. Test Unbalanced Error
    unbalanced_entries = [
        {"account_id": cash.id, "amount": -50.0},
        {"account_id": groceries.id, "amount": 40.0} # Missing 10
    ]
    with pytest.raises(ValueError, match="Transaction not balanced"):
        service.record_transaction(party.id, "Bad Txn", datetime.now(), unbalanced_entries)
