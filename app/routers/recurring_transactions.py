from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/recurring-transactions", tags=["recurring-transactions"])


def calculate_next_due_date(start_date: datetime, frequency: str) -> datetime:
    """Calculate next due date based on frequency (legacy function)"""
    if frequency == "DAILY":
        return start_date + timedelta(days=1)
    elif frequency == "WEEKLY":
        return start_date + timedelta(weeks=1)
    elif frequency == "MONTHLY":
        return start_date + relativedelta(months=1)
    elif frequency == "YEARLY":
        return start_date + relativedelta(years=1)
    else:
        return start_date + timedelta(days=30)  # Default to monthly


def calculate_next_due_date_enhanced(start_date: datetime, frequency: str, date_flexibility: str = "EXACT") -> datetime:
    """Enhanced calculation with date flexibility options"""
    # Base calculation
    if frequency == "DAILY":
        next_date = start_date + timedelta(days=1)
    elif frequency == "WEEKLY":
        next_date = start_date + timedelta(weeks=1)
    elif frequency == "BIWEEKLY":
        next_date = start_date + timedelta(weeks=2)
    elif frequency == "FOUR_WEEKLY":
        next_date = start_date + timedelta(weeks=4)
    elif frequency == "MONTHLY":
        next_date = start_date + relativedelta(months=1)
    elif frequency == "YEARLY":
        next_date = start_date + relativedelta(years=1)
    else:
        next_date = start_date + relativedelta(months=1)  # Default to monthly
    
    # Apply date flexibility
    if date_flexibility == "EARLY_MONTH":
        next_date = next_date.replace(day=1)
    elif date_flexibility == "MID_MONTH":
        next_date = next_date.replace(day=15)
    elif date_flexibility == "LATE_MONTH":
        # Last day of month
        next_date = next_date.replace(day=28)
    elif date_flexibility == "WEEKDAY":
        # Adjust to next weekday if falls on weekend
        while next_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            next_date += timedelta(days=1)
    elif date_flexibility == "WEEKEND":
        # Adjust to next weekend if falls on weekday
        while next_date.weekday() < 5:
            next_date += timedelta(days=1)
    
    return next_date


@router.post("", response_model=schemas.RecurringTransaction)
def create_recurring_transaction(
    recurring_transaction: schemas.RecurringTransactionCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Verify category belongs to user
    category = db.query(models.Category).filter(
        models.Category.id == recurring_transaction.category_id,
        models.Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Calculate next due date with enhanced logic
    next_due_date = calculate_next_due_date_enhanced(
        recurring_transaction.start_date, 
        recurring_transaction.frequency,
        recurring_transaction.date_flexibility
    )
    
    # Convert string enums to enum objects
    try:
        frequency_enum = models.RecurrenceFrequency(recurring_transaction.frequency)
        flexibility_enum = models.DateFlexibility(recurring_transaction.date_flexibility)
        priority_enum = models.TransactionPriority(recurring_transaction.priority)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {str(e)}")
    
    # Create the recurring transaction with proper enum values
    transaction_data = recurring_transaction.dict()
    transaction_data.pop('category_id')  # Remove to avoid conflict
    
    db_recurring_transaction = models.RecurringTransaction(
        **transaction_data,
        user_id=current_user.id,
        category_id=recurring_transaction.category_id,
        next_due_date=next_due_date,
        frequency=frequency_enum,
        date_flexibility=flexibility_enum,
        priority=priority_enum
    )
    
    db.add(db_recurring_transaction)
    db.commit()
    db.refresh(db_recurring_transaction)
    return db_recurring_transaction


@router.get("", response_model=List[schemas.RecurringTransaction])
def list_active_recurring_transactions(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.user_id == current_user.id,
        models.RecurringTransaction.is_active == True
    ).all()


@router.get("/{transaction_id}", response_model=schemas.RecurringTransaction)
def get_recurring_transaction(
    transaction_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    recurring_transaction = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.id == transaction_id,
        models.RecurringTransaction.user_id == current_user.id
    ).first()
    
    if not recurring_transaction:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    
    return recurring_transaction


@router.put("/{transaction_id}/status", response_model=schemas.RecurringTransaction)
def update_recurring_transaction_status(
    transaction_id: str,
    status_update: schemas.RecurringTransactionStatusUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    recurring_transaction = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.id == transaction_id,
        models.RecurringTransaction.user_id == current_user.id
    ).first()
    
    if not recurring_transaction:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    
    recurring_transaction.is_active = status_update.is_active
    db.commit()
    db.refresh(recurring_transaction)
    return recurring_transaction


@router.delete("/{transaction_id}")
def delete_recurring_transaction(
    transaction_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    recurring_transaction = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.id == transaction_id,
        models.RecurringTransaction.user_id == current_user.id
    ).first()
    
    if not recurring_transaction:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    
    db.delete(recurring_transaction)
    db.commit()
    return {"message": "Recurring transaction deleted successfully"}


@router.put("/{transaction_id}", response_model=schemas.RecurringTransaction)
def update_recurring_transaction(
    transaction_id: str,
    transaction_update: schemas.RecurringTransactionUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    recurring_transaction = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.id == transaction_id,
        models.RecurringTransaction.user_id == current_user.id
    ).first()
    
    if not recurring_transaction:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    
    update_data = transaction_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(recurring_transaction, field, value)
    
    # Recalculate next due date if frequency changed
    if "frequency" in update_data:
        recurring_transaction.next_due_date = calculate_next_due_date(
            recurring_transaction.start_date, 
            recurring_transaction.frequency
        )
    
    db.commit()
    db.refresh(recurring_transaction)
    return recurring_transaction