from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import List, Union
from datetime import datetime
import logging

from app.database import get_db
from app import models, schemas, auth
from app.routers.recurring_transactions import calculate_next_due_date_enhanced

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transactions", tags=["transactions"])


def handle_recurrence_creation(transaction: models.Transaction, recurrence_data: schemas.RecurrenceData, db: Session):
    """Create a new RecurringTransaction from transaction and recurrence data"""
    try:
        # Convert string enums to enum objects
        frequency_enum = models.RecurrenceFrequency(recurrence_data.frequency)
        flexibility_enum = models.DateFlexibility(recurrence_data.date_flexibility)
        
        # Calculate next due date
        next_due_date = calculate_next_due_date_enhanced(
            recurrence_data.start_date,
            recurrence_data.frequency,
            recurrence_data.date_flexibility
        )
        
        # Create RecurringTransaction
        recurring_transaction = models.RecurringTransaction(
            description=transaction.description,
            amount=transaction.amount,
            type=transaction.type,
            frequency=frequency_enum,
            date_flexibility=flexibility_enum,
            range_start=recurrence_data.range_start,
            range_end=recurrence_data.range_end,
            preference=recurrence_data.preference,
            start_date=recurrence_data.start_date,
            next_due_date=next_due_date,
            is_variable_amount=recurrence_data.is_variable_amount or False,
            estimated_min_amount=recurrence_data.estimated_min_amount,
            estimated_max_amount=recurrence_data.estimated_max_amount,
            user_id=transaction.user_id,
            category_id=transaction.category_id,
            source_transaction_id=transaction.id,
            priority=models.TransactionPriority.MEDIUM  # Default priority
        )
        
        db.add(recurring_transaction)
        db.flush()  # Get the ID without committing
        # Link the original transaction to the new recurring transaction
        transaction.recurring_transaction_id = recurring_transaction.id
        db.commit()
        db.refresh(recurring_transaction)
        db.refresh(transaction)
        return recurring_transaction
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid recurrence data: {str(e)}")


def handle_recurrence_update(transaction: models.Transaction, recurrence_data: schemas.RecurrenceData, db: Session):
    """Update existing RecurringTransaction"""
    recurring_transaction = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.id == recurrence_data.id,
        models.RecurringTransaction.user_id == transaction.user_id
    ).first()
    
    if not recurring_transaction:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    
    try:
        # Convert string enums to enum objects
        frequency_enum = models.RecurrenceFrequency(recurrence_data.frequency)
        flexibility_enum = models.DateFlexibility(recurrence_data.date_flexibility)
        
        # Update fields
        recurring_transaction.frequency = frequency_enum
        recurring_transaction.date_flexibility = flexibility_enum
        recurring_transaction.range_start = recurrence_data.range_start
        recurring_transaction.range_end = recurrence_data.range_end
        recurring_transaction.preference = recurrence_data.preference
        recurring_transaction.start_date = recurrence_data.start_date
        recurring_transaction.is_variable_amount = recurrence_data.is_variable_amount or False
        recurring_transaction.estimated_min_amount = recurrence_data.estimated_min_amount
        recurring_transaction.estimated_max_amount = recurrence_data.estimated_max_amount
        
        # Recalculate next due date
        recurring_transaction.next_due_date = calculate_next_due_date_enhanced(
            recurrence_data.start_date,
            recurrence_data.frequency,
            recurrence_data.date_flexibility
        )
        
        return recurring_transaction
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid recurrence data: {str(e)}")


def handle_recurrence_removal(transaction: models.Transaction, db: Session):
    """Remove RecurringTransaction associated with this transaction"""
    recurring_transaction = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.source_transaction_id == transaction.id,
        models.RecurringTransaction.user_id == transaction.user_id
    ).first()
    
    if recurring_transaction:
        db.delete(recurring_transaction)


def convert_recurring_to_recurrence_data(recurring_transaction: models.RecurringTransaction) -> schemas.RecurrenceData:
    """Convert RecurringTransaction model to RecurrenceData schema"""
    if not recurring_transaction:
        return None
        
    return schemas.RecurrenceData(
        id=recurring_transaction.id,
        frequency=recurring_transaction.frequency,
        start_date=recurring_transaction.start_date,
        date_flexibility=recurring_transaction.date_flexibility,
        range_start=recurring_transaction.range_start,
        range_end=recurring_transaction.range_end,
        preference=recurring_transaction.preference,
        is_variable_amount=recurring_transaction.is_variable_amount,
        estimated_min_amount=recurring_transaction.estimated_min_amount,
        estimated_max_amount=recurring_transaction.estimated_max_amount
    )


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
    
    # Refresh created transactions
    for transaction in created_transactions:
        db.refresh(transaction)
    
    # Invalidate rollover calculations for affected months
    try:
        from .budgets import invalidate_rollover_chain
        affected_months = set()
        
        for transaction in created_transactions:
            transaction_month = transaction.date.strftime('%Y-%m')
            affected_months.add(transaction_month)
        
        for month in affected_months:
            invalidate_rollover_chain(db, current_user.id, month, "transaction_created")
        
        db.commit()  # Commit rollover invalidation
    except Exception as e:
        logger.warning(f"Failed to invalidate rollover after transaction creation: {e}")
    
    # Return single transaction if input was single, otherwise return list
    if len(created_transactions) == 1:
        return created_transactions[0]
    return created_transactions


@router.get("", response_model=List[schemas.Transaction])
def list_transactions(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.is_deleted == False
    ).all()
    
    # Build response with recurrence data
    response_transactions = []
    for transaction in transactions:
        transaction_dict = {
            "id": transaction.id,
            "type": transaction.type,
            "description": transaction.description,
            "amount": transaction.amount,
            "occurred_on": transaction.occurred_on,
            "personal_share": transaction.personal_share,
            "owed_share": transaction.owed_share,
            "share_metadata": transaction.share_metadata,
            "user_id": transaction.user_id,
            "category_id": transaction.category_id,
            "is_deleted": transaction.is_deleted,
            "refunded": transaction.refunded,
            "created_at": transaction.created_at,
            "category": transaction.category,
            "recurrence": convert_recurring_to_recurrence_data(transaction.recurring_transaction) if transaction.recurring_transaction else None
        }
        response_transactions.append(schemas.Transaction(**transaction_dict))
    
    return response_transactions


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
        
        # Handle recurrence data
        if hasattr(update, 'recurrence'):
            if update.recurrence is not None:
                # Create or update recurrence
                if update.recurrence.id:
                    # Update existing recurrence
                    handle_recurrence_update(transaction, update.recurrence, db)
                else:
                    # Create new recurrence
                    handle_recurrence_creation(transaction, update.recurrence, db)
            else:
                # Remove recurrence (recurrence is explicitly None)
                handle_recurrence_removal(transaction, db)
        
        # Update regular transaction fields (exclude recurrence from the update)
        update_data = update.dict(exclude_unset=True, exclude={'id', 'recurrence'})
        for field, value in update_data.items():
            setattr(transaction, field, value)
        
        updated_transactions.append(transaction)
    
    db.commit()
    
    # Refresh all transactions and build response with recurrence data
    for transaction in updated_transactions:
        db.refresh(transaction)
        # Load the recurring transaction relationship if it exists
        if transaction.recurring_transaction:
            db.refresh(transaction.recurring_transaction)
    
    # Build response transactions with recurrence data
    response_transactions = []
    for transaction in updated_transactions:
        transaction_dict = {
            "id": transaction.id,
            "type": transaction.type,
            "description": transaction.description,
            "amount": transaction.amount,
            "occurred_on": transaction.occurred_on,
            "personal_share": transaction.personal_share,
            "owed_share": transaction.owed_share,
            "share_metadata": transaction.share_metadata,
            "user_id": transaction.user_id,
            "category_id": transaction.category_id,
            "is_deleted": transaction.is_deleted,
            "refunded": transaction.refunded,
            "created_at": transaction.created_at,
            "category": transaction.category,
            "recurrence": convert_recurring_to_recurrence_data(transaction.recurring_transaction) if transaction.recurring_transaction else None
        }
        response_transactions.append(schemas.Transaction(**transaction_dict))
    
    # Invalidate rollover calculations for affected months
    try:
        from .budgets import invalidate_rollover_chain
        affected_months = set()
        
        for transaction in updated_transactions:
            transaction_month = transaction.date.strftime('%Y-%m')
            affected_months.add(transaction_month)
        
        for month in affected_months:
            invalidate_rollover_chain(db, current_user.id, month, "transaction_updated")
        
        db.commit()  # Commit rollover invalidation
    except Exception as e:
        logger.warning(f"Failed to invalidate rollover after transaction update: {e}")
    
    # Return single transaction if input was single, otherwise return list
    if len(response_transactions) == 1:
        return response_transactions[0]
    return response_transactions


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
    
    # Build response with recurrence data
    response_transactions = []
    for transaction in transactions:
        transaction_dict = {
            "id": transaction.id,
            "type": transaction.type,
            "description": transaction.description,
            "amount": transaction.amount,
            "occurred_on": transaction.occurred_on,
            "personal_share": transaction.personal_share,
            "owed_share": transaction.owed_share,
            "share_metadata": transaction.share_metadata,
            "user_id": transaction.user_id,
            "category_id": transaction.category_id,
            "is_deleted": transaction.is_deleted,
            "refunded": transaction.refunded,
            "created_at": transaction.created_at,
            "category": transaction.category,
            "recurrence": convert_recurring_to_recurrence_data(transaction.recurring_transaction) if transaction.recurring_transaction else None
        }
        response_transactions.append(schemas.Transaction(**transaction_dict))
    
    return response_transactions


@router.post("/budget-impact-preview")
def preview_budget_impact(
    transaction_data: schemas.TransactionCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Preview how a transaction would impact budgets before creating it"""
    # Verify category belongs to user
    category = db.query(models.Category).filter(
        models.Category.id == transaction_data.category_id,
        models.Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Simple preview without complex budget integration
    if transaction_data.type != "EXPENSE":
        return {"affected_budgets": [], "warnings": [], "message": "Non-expense transactions don't affect budgets"}
    
    return {"message": "Budget impact preview not available in simplified mode"}