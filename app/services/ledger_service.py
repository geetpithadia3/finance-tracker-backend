```python
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from datetime import datetime
from typing import List, Optional

from app.models import Party, Account, LedgerTransaction, Entry
import logging

logger = logging.getLogger("finance_tracker.ledger")

class LedgerService:
    def __init__(self, db: Session):
        self.db = db

    def create_party(self, type: str, name: str) -> Party:
        party = Party(type=type, name=name)
        self.db.add(party)
        self.db.commit()
        self.db.refresh(party)
        return party

    def create_account(self, owner_id: str, name: str, type: str, parent_id: str = None) -> Account:
        account = Account(
            owner_id=owner_id,
            name=name,
            type=type, # 'ASSET', 'LIABILITY', 'INCOME', 'EXPENSE'
            parent_id=parent_id
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def record_transaction(self, owner_id: str, description: str, date, entries_data: list) -> LedgerTransaction:
        """Record a balanced double-entry transaction"""
        logger.debug(f"Recording transaction for owner {owner_id}: {description}")
        # Verify balance
        total = sum(e['amount'] for e in entries_data)
        if abs(total) > 0.0001:
             raise ValueError(f"Transaction not balanced: {total}")
        
        transaction = LedgerTransaction(
            owner_id=owner_id,
            description=description,
            date=date
        )
        self.db.add(transaction)
        self.db.flush() # Get ID
        
        for e_data in entries_data:
            entry = Entry(
                transaction_id=transaction.id,
                account_id=e_data['account_id'],
                amount=e_data['amount']
            )
            self.db.add(entry)
            
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
    
    def seed_default_accounts(self, party_id: str):
        # Create Root Accounts
        self.create_account(party_id, "Assets", "ASSET")
        self.create_account(party_id, "Liabilities", "LIABILITY")
        self.create_account(party_id, "Income", "INCOME")
        self.create_account(party_id, "Expenses", "EXPENSE")
        
        # Create Common Accounts
        # checking = self.create_account(party_id, "Checking", "ASSET") # Real implementation would link to Assets parent
        self.create_account(party_id, "Cash", "ASSET")
        self.create_account(party_id, "Groceries", "EXPENSE")
        self.create_account(party_id, "Salary", "INCOME")

    def get_accounts(self, owner_id: str, type: str = None) -> List[Account]:
        query = self.db.query(Account).filter(Account.owner_id == owner_id, Account.is_active == True)
        if type:
            query = query.filter(Account.type == type)
        return query.all()

    def get_account_by_name(self, owner_id: str, name: str) -> Optional[Account]:
        return self.db.query(Account).filter(
            Account.owner_id == owner_id, 
            Account.name == name,
            Account.is_active == True
        ).first()

    def get_account(self, account_id: str) -> Optional[Account]:
        return self.db.query(Account).filter(Account.id == account_id).first()
        
    def get_or_create_default_asset_account(self, owner_id: str) -> Account:
        """Helper for MVP: get a default 'Cash' or 'Source' account"""
        acc = self.get_account_by_name(owner_id, "Cash")
        if not acc:
            acc = self.create_account(owner_id, "Cash", "ASSET")
        return acc

    def get_or_create_account(self, owner_id: str, name: str, account_type: str) -> Account:
        """Get or create an account by name"""
        acc = self.get_account_by_name(owner_id, name)
        if not acc:
            acc = self.create_account(owner_id, name, account_type)
        return acc
