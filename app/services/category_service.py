"""
Category Service Generic Adapter (V2)
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.services.ledger_service import LedgerService
from app.core.exceptions import raise_http_exception
from app.schemas import CategoryCreate, CategoryUpdate, Category as CategorySchema
from app.models import User, Account

class CategoryService:
    """
    Adapter Service:
    Maps "Category" operations to V2 "Account" operations.
    Categories defined as Accounts of type 'EXPENSE'.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ledger = LedgerService(db)

    def create_category(self, data: CategoryCreate, user: User) -> CategorySchema:
        if not user.party_id:
             # Basic safety, though Auth service creates party
             raise_http_exception(400, "User has no initialized Party (V2).")

        # In V2, creating a Category = Creating an EXPENSE Account
        account = self.ledger.create_account(
            owner_id=user.party_id,
            name=data.name,
            type="EXPENSE"
        )
        return self._to_schema(account, user.id)

    def get_user_categories(self, user: User, household_id: str = None, include_household: bool = True, show_usage: bool = False) -> List[CategorySchema]:
        if not user.party_id:
            return []

        # Get EXPENSE accounts
        accounts = self.ledger.get_accounts(user.party_id, "EXPENSE")
        return [self._to_schema(acc, user.id) for acc in accounts]

    def get_category_by_id(self, category_id: str, user: User) -> CategorySchema:
        account = self.ledger.get_account(category_id)
        if not account or account.owner_id != user.party_id:
             # Simple permission check: User owns the party
             raise_http_exception(404, "Category not found")
        return self._to_schema(account, user.id)

    def seed_default_categories(self, user: User) -> List[CategorySchema]:
        # Ledger Service has a seeder
        if not user.party_id:
            # Create party on the fly if missing (recovery)
             party = self.ledger.create_party("USER", user.username)
             user.party_id = party.id
             self.db.add(user)
             self.db.commit()

        self.ledger.seed_default_accounts(user.party_id)
        # Fetch them back
        return self.get_user_categories(user)

    def _to_schema(self, account: Account, user_id: str) -> CategorySchema:
        """Map Account -> Category Schema"""
        # Map owner_id to user_id for API compatibility
        return CategorySchema(
            id=account.id,
            name=account.name,
            user_id=user_id, # Assuming single user ownership for MVP
            household_id=None
        )

    # --- Stubs for strict API compatibility if Router calls them ---
    # The Router calls these methods, so we must define them, even if they No-Op or Error.
    
    def seed_custom_categories(self, names: List[str], user: User) -> List[CategorySchema]:
        created = []
        for name in names:
            acc = self.ledger.create_account(
                owner_id=user.party_id, 
                name=name, 
                type="EXPENSE"
            )
            created.append(self._to_schema(acc, user.id))
        return created

    def update_category(self, id: str, data: CategoryUpdate, user: User):
        # MVP: Just update name
        acc = self.ledger.get_account(id)
        if acc and data.name:
            acc.name = data.name
            self.db.commit()
            self.db.refresh(acc)
            return self._to_schema(acc, user.id)
        raise_http_exception(404, "Category not found")

    def delete_category(self, id: str, user: User):
        acc = self.ledger.get_account(id)
        if acc:
            acc.is_active = False # Soft delete
            self.db.commit()

    def search_categories(self, q: str, user: User, household_id: str=None, limit: int=50):
         # Needs a search method in Ledger
         # For MVP, fetch all and filter in python (inefficient but safe)
         all_cats = self.get_user_categories(user)
         return [c for c in all_cats if q.lower() in c.name.lower()][:limit]
    
    def get_category_statistics(self, *args, **kwargs):
        # Stub
        return {"total_categories": 0}

    def get_default_categories_info(self):
        # Stub
        return [{"name": "Groceries"}, {"name": "Utilities"}]
