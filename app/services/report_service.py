"""
Report Service (V2)
Aggregates Ledger Entries for Financial Reporting
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Entry, Account, LedgerTransaction, User

class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_expenses_by_category(self, user: User, year: int, month: int) -> List[Dict[str, Any]]:
        """
        Sum positive entries in EXPENSE accounts for a given month.
        """
        if not user.party_id:
             return []

        # Logic:
        # 1. Join Entries -> LedgerTransaction to filter by Date
        # 2. Join Entries -> Account to filter by Type=EXPENSE and Owner=Party
        # 3. Group by Account
        
        results = (
            self.db.query(
                Account.name,
                func.sum(Entry.amount).label("total")
            )
            .join(LedgerTransaction, Entry.transaction_id == LedgerTransaction.id)
            .join(Account, Entry.account_id == Account.id)
            .filter(
                Account.owner_id == user.party_id,
                Account.type == "EXPENSE",
                func.extract('year', LedgerTransaction.date) == year,
                func.extract('month', LedgerTransaction.date) == month,
                Entry.amount > 0 # Expenses are Debits (positive)
            )
            .group_by(Account.name)
            .all()
        )
        
        return [{"category": name, "amount": float(total)} for name, total in results]

    def get_monthly_summary(self, user: User, year: int, month: int) -> Dict[str, float]:
        """
        Get Total Income vs Total Expenses for a month.
        """
        if not user.party_id:
            return {"income": 0.0, "expenses": 0.0, "net": 0.0}
            
        # Expenses: Sum of Debits to EXPENSE accounts
        expenses = (
            self.db.query(func.sum(Entry.amount))
            .join(LedgerTransaction, Entry.transaction_id == LedgerTransaction.id)
            .join(Account, Entry.account_id == Account.id)
            .filter(
                Account.owner_id == user.party_id,
                Account.type == "EXPENSE",
                func.extract('year', LedgerTransaction.date) == year,
                func.extract('month', LedgerTransaction.date) == month,
                Entry.amount > 0
            )
            .scalar()
        ) or 0.0
        
        # Income: Sum of Credits to INCOME accounts (negative numbers usually)
        # But wait, Credits are negative in our system.
        # Income increases with Credit.
        # So we want sum(abs(amount)) for CREDIT entries to INCOME accounts
        income_neg = (
            self.db.query(func.sum(Entry.amount))
            .join(LedgerTransaction, Entry.transaction_id == LedgerTransaction.id)
            .join(Account, Entry.account_id == Account.id)
            .filter(
                Account.owner_id == user.party_id,
                Account.type == "INCOME",
                func.extract('year', LedgerTransaction.date) == year,
                func.extract('month', LedgerTransaction.date) == month,
                Entry.amount < 0
            )
            .scalar()
        ) or 0.0
        
        income = abs(income_neg)
        
        return {
            "income": income,
            "expenses": expenses,
            "net": income - expenses
        }
