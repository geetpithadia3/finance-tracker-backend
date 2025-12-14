"""
Refactored transactions router using the new layered architecture
Maintains original API paths for backwards compatibility
"""
from fastapi import APIRouter, Depends, status, Query, HTTPException
from typing import List, Optional
from app import schemas, auth
from app.models import User
from app.services.transaction_service import TransactionService
from app.core.dependencies import get_transaction_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=List[schemas.Transaction], status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction_data: schemas.TransactionCreate,
    current_user: User = Depends(auth.get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
    household_id: Optional[str] = Query(None, description="Household ID for shared transactions")
):
    """Create a new transaction (or multiple for splits)"""
    return transaction_service.create_transaction(
        transaction_data, current_user, household_id
    )


@router.get("", response_model=List[schemas.Transaction])
def get_transactions(
    current_user: User = Depends(auth.get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month"),
    category_id: Optional[str] = Query(None, description="Filter by category"),
    household_id: Optional[str] = Query(None, description="Include household transactions"),
    skip: int = Query(0, ge=0, description="Skip records for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Limit records for pagination")
):
    """Get transactions with optional filters"""
    return transaction_service.get_user_transactions(
        current_user, year=year, month=month, category_id=category_id
    )