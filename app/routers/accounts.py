"""
Accounts Router (V2)
Manages Asset/Liability Accounts (Payment Methods)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app import auth
from app.services.ledger_service import LedgerService
from app.schemas import AccountCreate, AccountResponse
from app.core import dependencies

router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
    responses={404: {"description": "Not found"}},
)

def get_ledger_service(db: Session = Depends(get_db)) -> LedgerService:
    return LedgerService(db)

@router.post("/", response_model=AccountResponse, status_code=201)
def create_account(
    data: AccountCreate,
    current_user: User = Depends(auth.get_current_user),
    service: LedgerService = Depends(get_ledger_service)
):
    """
    Create a new account (Asset, Liability, etc).
    """
    if not current_user.party_id:
         raise HTTPException(status_code=400, detail="User has no party")

    account = service.create_account(current_user.party_id, data.name, data.type)
    return account

@router.get("/", response_model=List[AccountResponse])
def list_accounts(
    type: Optional[str] = Query(None, description="Filter by account type (ASSET, LIABILITY, etc)"),
    current_user: User = Depends(auth.get_current_user),
    service: LedgerService = Depends(get_ledger_service)
):
    """
    List accounts.
    If no type is specified, returns ASSET and LIABILITY (Payment Methods).
    """
    if not current_user.party_id:
        return []

    if type:
        accounts = service.get_accounts(current_user.party_id, type.upper())
    else:
        # Default: Assets and Liabilities (so user can pick payment method)
        assets = service.get_accounts(current_user.party_id, "ASSET")
        liabilities = service.get_accounts(current_user.party_id, "LIABILITY")
        accounts = assets + liabilities
        
    return accounts
