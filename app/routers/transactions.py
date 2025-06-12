from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import List, Union

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("")
def create_transactions(
    transactions: Union[schemas.TransactionCreate, List[schemas.TransactionCreate]],
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Handle both single transaction and list of transactions
    if not isinstance(transactions, list):
        transactions = [transactions]
    
    created_transactions = []
    
    for transaction in transactions:
        # Verify category belongs to user
        category = db.query(models.Category).filter(
            models.Category.id == transaction.category_id,
            models.Category.user_id == current_user.id
        ).first()
        
        if not category:
            raise HTTPException(status_code=404, detail=f"Category {transaction.category_id} not found")
        
        db_transaction = models.Transaction(**transaction.dict(), user_id=current_user.id)
        db.add(db_transaction)
        created_transactions.append(db_transaction)
    
    db.commit()
    
    # Refresh all transactions
    for transaction in created_transactions:
        db.refresh(transaction)
    
    # Return single transaction if input was single, otherwise return list
    if len(created_transactions) == 1:
        return created_transactions[0]
    return created_transactions


@router.get("", response_model=List[schemas.Transaction])
def list_transactions(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.is_deleted == False
    ).all()


@router.put("")
def update_transactions(
    updates: Union[schemas.TransactionUpdate, List[schemas.TransactionUpdate]],
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Handle both single update and list of updates
    if not isinstance(updates, list):
        updates = [updates]
    
    updated_transactions = []
    
    for update in updates:
        transaction = db.query(models.Transaction).filter(
            models.Transaction.id == update.id,
            models.Transaction.user_id == current_user.id
        ).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail=f"Transaction {update.id} not found")
        
        # Verify category belongs to user if category_id is being updated
        if update.category_id and update.category_id != transaction.category_id:
            category = db.query(models.Category).filter(
                models.Category.id == update.category_id,
                models.Category.user_id == current_user.id
            ).first()
            
            if not category:
                raise HTTPException(status_code=404, detail=f"Category {update.category_id} not found")
        
        update_data = update.dict(exclude_unset=True, exclude={'id'})
        for field, value in update_data.items():
            setattr(transaction, field, value)
        
        updated_transactions.append(transaction)
    
    db.commit()
    
    # Refresh all transactions
    for transaction in updated_transactions:
        db.refresh(transaction)
    
    # Return single transaction if input was single, otherwise return list
    if len(updated_transactions) == 1:
        return updated_transactions[0]
    return updated_transactions


@router.put("/{transaction_id}", response_model=schemas.Transaction)
def update_single_transaction(
    transaction_id: str,
    transaction_update: schemas.TransactionUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Set the id from path parameter
    transaction_update.id = transaction_id
    
    # Use the bulk update function with single item
    result = update_transactions(transaction_update, current_user, db)
    return result


@router.post("/list", response_model=List[schemas.Transaction])
def list_transactions_by_month(
    request: schemas.ListTransactionsByMonthRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.is_deleted == False,
        extract('year', models.Transaction.occurred_on) == request.year,
        extract('month', models.Transaction.occurred_on) == request.month
    ).all()
    
    return transactions