"""
Centralized security and permission management (V2)
"""
from sqlalchemy.orm import Session
from app import models
from app.core.exceptions import raise_not_found, raise_unauthorized
from app.services.ledger_service import LedgerService
import logging

logger = logging.getLogger(__name__)

class SecurityService:
    """Centralized security and permission checks"""
    
    @staticmethod
    def verify_account_access(db: Session, account_id: str, current_user: models.User):
        ledger = LedgerService(db)
        account = ledger.get_account(account_id)
        
        if not account:
            raise_not_found("Account/Category", account_id)
            
        if account.owner_id != current_user.party_id:
             raise_unauthorized(f"access to account {account_id}")
             
        return account

    # --- Stubs/Aliases for Adapters ---
    
    @staticmethod
    def verify_category_access(db: Session, category_id: str, current_user: models.User, household_id: str = None):
        """Adapter: Category ID is actually Account ID"""
        return SecurityService.verify_account_access(db, category_id, current_user)

    @staticmethod
    def check_household_member_permission(*args, **kwargs):
        # Households removed in MVP V2 hard cutover
        raise_unauthorized("Households not supported in V2 yet")