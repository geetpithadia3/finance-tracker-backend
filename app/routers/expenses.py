from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import List
from datetime import date

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=List[schemas.ExpenseResponse])
def list_expenses_by_month(
    year: int = None,
    month: int = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Default to current month if not specified
    if not year or not month:
        today = date.today()
        year = year or today.year
        month = month or today.month
    
    expenses = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.type == "EXPENSE",
        models.Transaction.is_deleted == False,
        extract('year', models.Transaction.occurred_on) == year,
        extract('month', models.Transaction.occurred_on) == month
    ).all()
    
    return expenses


@router.post("/list", response_model=List[schemas.ExpenseResponse])
def list_expenses_by_month_post(
    request: schemas.ListExpensesByMonthRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    expenses = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.type == "EXPENSE",
        models.Transaction.is_deleted == False,
        extract('year', models.Transaction.occurred_on) == request.year,
        extract('month', models.Transaction.occurred_on) == request.month
    ).all()
    
    return expenses