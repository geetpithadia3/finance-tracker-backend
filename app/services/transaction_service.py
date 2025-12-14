"""
Transaction Service Generic Adapter (V2)
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.services.ledger_service import LedgerService
from app.core.error_handler import raise_http_exception
import logging

logger = logging.getLogger("finance_tracker.transactions")
from app.schemas import TransactionCreate, TransactionUpdate, Transaction as TransactionSchema
from app.models import User, LedgerTransaction, Entry, Account

class TransactionService:
    """
    Adapter Service:
    Maps "Transaction" operations to V2 "Ledger" operations.
    """
    
    def __init__(self, db: Session, ledger_service: LedgerService = None):
        self.db = db
        # If injected, use it, else create new
        self.ledger = ledger_service if ledger_service else LedgerService(db)

    def create_transaction(self, data: TransactionCreate, user: User, household_id: str = None) -> list[TransactionSchema]:
        logger.info(f"Creating transaction for user {user.username}: {data.description}")
        if not user.party_id:
             raise_http_exception(400, "User has no party")

        # 1. Get Source (Asset/Liability)
        if data.source_account_id:
            # Verify explicit source
            source_account = self.ledger.get_account(data.source_account_id)
            if not source_account or source_account.owner_id != user.party_id:
                raise_http_exception(400, "Invalid source account")
        else:
            # Fallback: Default 'Cash'
            source_account = self.ledger.get_or_create_default_asset_account(user.party_id)
        
        # 2. Get Destination (Expense/Category)
        # data.category_id is expected to be an Account ID now
        # Ideally verify it is valid and owned by party, but LedgerService will catch FK error
        
        # 3. Construct Entries
        # Expense = DEBIT (+), Asset = CREDIT (-)
        # If paying by Credit Card (Liability):
        # Liability increases on Credit (-).
        # Expense increases on Debit (+).
        # So the logic holds: Credit the Source, Debit the Destination.
        
        amount = abs(data.amount)
        entries = []
        
        if data.type == "TRANSFER":
            # Transfer Logic: Source -> Destination
            if not data.destination_account_id:
                raise_http_exception(400, "Destination account required for transfer")
                
            # Validations?
            
            entries = [
                {"account_id": source_account.id, "amount": -amount}, # Credit Source
                {"account_id": data.destination_account_id, "amount": amount} # Debit Destination
            ]
            
            # For response schema, we might map destination as category_id
            data.category_id = data.destination_account_id
            
        elif data.splits:
            # Split Logic: Create separate transactions for each split
            logger.info(f"Processing split transaction with {len(data.splits)} splits")
            results = []
            for split in data.splits:
                split_amount = abs(split.amount)
                entries = [
                    {"account_id": source_account.id, "amount": -split_amount},
                    {"account_id": split.category_id, "amount": split_amount}
                ]
                
                txn = self.ledger.record_transaction(
                    owner_id=user.party_id,
                    description=split.description,
                    date=data.occurred_on,
                    entries_data=entries
                )
                results.append(self._to_schema(txn, user.id, split.category_id, split_amount))
            
            return results

        elif data.share:
             # Share Logic (Reimbursable)
             logger.info(f"Processing shared expense: {data.share.method} - {data.share.value}")
             # Calculate Personal Amount
             personal_amt = 0.0
             
             method = data.share.method
             val = data.share.value
             
             if method == "FIXED":
                 personal_amt = val
             elif method == "PERCENTAGE":
                 personal_amt = amount * (val / 100.0)
             elif method == "EQUAL":
                 # Value is count of people (e.g. 2 for 50/50)
                 if val <= 0: val = 1
                 personal_amt = amount / val

             # Validation
             if personal_amt < 0 or personal_amt > amount + 0.01: # epsilon
                 raise_http_exception(400, f"Personal amount {personal_amt} invalid for total {amount}")

             # Rounding
             personal_amt = round(personal_amt, 2)
             reimbursable_amt = round(amount - personal_amt, 2)
             
             # Create Reimbursable Account if needed
             reimbursable_account = self.ledger.get_or_create_account(
                 owner_id=user.party_id,
                 name="Reimbursable",
                 account_type="ASSET"
             )
             
             # Entries: Credit Source, Debit Category (Personal), Debit Reimbursable
             entries.append({"account_id": source_account.id, "amount": -amount})
             if personal_amt > 0:
                 entries.append({"account_id": data.category_id, "amount": personal_amt})
             if reimbursable_amt > 0:
                 entries.append({"account_id": reimbursable_account.id, "amount": reimbursable_amt})

        else:
            # Standard Expense
            entries = [
                {"account_id": source_account.id, "amount": -amount}, # Credit Source
                {"account_id": data.category_id, "amount": amount} # Debit Category
            ]
        
        # 4. Record
        txn = self.ledger.record_transaction(
            owner_id=user.party_id,
            description=data.description,
            date=data.occurred_on,
            entries_data=entries
        )
        
        return [self._to_schema(txn, user.id, data.category_id, amount)]

    def get_user_transactions(self, user: User, **kwargs) -> List[TransactionSchema]:
        # Fetch Ledger Transactions
        # Optimally we should filter by owner_id
        txns = self.db.query(LedgerTransaction).filter(
            LedgerTransaction.owner_id == user.party_id
        ).order_by(desc(LedgerTransaction.date)).limit(100).all()
        
        results = []
        for txn in txns:
            # Rehydrate Schema
            # For splits, we need to sum all positive (debit) entries
            # For simple transactions, there's only one
            positive_entries = [e for e in txn.entries if e.amount > 0]
            
            if positive_entries:
                # Sum all positive amounts (handles splits correctly)
                amount = sum(e.amount for e in positive_entries)
                # Use first positive entry's account as primary category
                cat_id = positive_entries[0].account_id
            else:
                # Fallback for weird transactions (e.g. Transfers)
                cat_id = "unknown"
                amount = 0.0
            
            results.append(self._to_schema(txn, user.id, cat_id, amount))
            
        return results

    def _to_schema(self, txn: LedgerTransaction, user_id: str, category_id: str, amount: float) -> TransactionSchema:
        # Determine type based on entries if possible
        # Simple heuristic: If category_id is "Transfer", it's a TRANSFER
        # But category_id is just an ID.
        
        return TransactionSchema(
            id=txn.id,
            user_id=user_id,
            category_id=category_id,
            type="EXPENSE", # Default to Expense for now to satisfy schema enum [CREDIT, DEBIT]
            description=txn.description,
            amount=amount,
            occurred_on=txn.date,
            created_at=txn.date
        )

    # --- Stubs ---
    def get_transaction_summary(self, *args, **kwargs):
        return {"total_income": 0, "total_expenses": 0}
    
    def get_category_spending_analysis(self, *args, **kwargs):
        return {}

    def search_transactions(self, *args, **kwargs):
        return []