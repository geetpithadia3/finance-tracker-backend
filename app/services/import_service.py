"""
CSV Import Service (V2)
"""
import csv
import io
from typing import List, Dict, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.ledger_service import LedgerService
from app.services.mapping_service import MappingService
from app.models import User
from app.core.exceptions import raise_http_exception
import logging

logger = logging.getLogger(__name__)

class ImportService:
    def __init__(self, db: Session):
        self.db = db
        self.ledger = LedgerService(db)
        self.mapping = MappingService(db)

    def import_transactions_csv(self, file_content: bytes, user: User) -> Dict[str, int]:
        """
        Parses a CSV file and creates V2 ledger transactions.
        
        Assumed CSV Format (Simple):
        Date, Description, Amount, Category (optional)
        2024-01-01, Grocery Store, 50.00, Groceries
        
        Returns:
            Dict: {"imported": int, "skipped": int}
        """
        if not user.party_id:
             raise_http_exception(400, "User has no initialized Party.")

        try:
            # Decode file
            content = file_content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Helper: Get all expense accounts for lookup (Name -> ID)
            accounts = self.ledger.get_accounts(user.party_id, "EXPENSE")
            account_map = {acc.name.lower(): acc.id for acc in accounts}
            
            # Default "Uncategorized" account
            uncategorized_id = account_map.get("uncategorized")
            if not uncategorized_id:
                # If not exists, create it
                acc = self.ledger.create_account(user.party_id, "Uncategorized", "EXPENSE")
                uncategorized_id = acc.id
            
            # Load Auto-Rules
            rules = self.mapping.get_rules(user.party_id)
            
            # Get default source (Cash)
            source_acc = self.ledger.get_or_create_default_asset_account(user.party_id)
            
            count = 0
            skipped = 0
            
            for row in csv_reader:
                try:
                    # Clean keys (trim whitespace)
                    row = {k.strip(): v.strip() for k, v in row.items() if k}
                    
                    # 1. Parse Date
                    # Try a few formats
                    date_str = row.get("Date", "")
                    occurred_on = self._parse_date(date_str)
                    
                    # 2. Parse Amount
                    amount_str = row.get("Amount", "0")
                    amount = float(amount_str.replace("$", "").replace(",", ""))
                    
                    # 3. Parse Description
                    description = row.get("Description", "Imported Transaction")
                    
                    # 4. Determine Category/Account
                    cat_name = row.get("Category", "").lower()
                    target_category_id = None
                    
                    # A. Explicit in CSV
                    if cat_name:
                        target_category_id = account_map.get(cat_name)
                    
                    # B. Auto-Rules (if not explicitly matched yet)
                    if not target_category_id:
                        target_category_id = self.mapping.apply_rules(user.party_id, description)
                        
                    # C. Uncategorized (Fallback)
                    if not target_category_id:
                        target_category_id = uncategorized_id
                    
                    # 5. Record Transaction (Double Entry)
                    # Simple assumption: Expense is positive in CSV
                    # Debit Expense, Credit Asset
                    amount = abs(amount)
                    entries = [
                        {"account_id": source_acc.id, "amount": -amount},
                        {"account_id": target_category_id, "amount": amount}
                    ]
                    
                    self.ledger.record_transaction(
                        owner_id=user.party_id,
                        description=description,
                        date=occurred_on,
                        entries_data=entries
                    )
                    count += 1
                    
                except Exception as e:
                    logger.warning(f"Skipping row {row}: {e}")
                    skipped += 1
            
            return {"imported": count, "skipped": skipped}
            
        except Exception as e:
            logger.error(f"CSV Parse Error: {e}")
            raise_http_exception(400, "Failed to parse CSV file.")

    def _parse_date(self, date_str: str) -> datetime:
        formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return datetime.now() # Fallback
