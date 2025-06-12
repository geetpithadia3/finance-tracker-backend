from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardResponse)
def get_dashboard(
    year_month: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Default to current month if not specified
    if not year_month:
        today = date.today()
        year_month = f"{today.year}-{today.month:02d}"
    
    year, month = map(int, year_month.split('-'))
    
    # Get transactions for specified month
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.is_deleted == False,
        extract('year', models.Transaction.occurred_on) == year,
        extract('month', models.Transaction.occurred_on) == month
    ).all()
    
    total_income = sum(t.amount for t in transactions if t.type == "INCOME")
    total_expenses = sum(t.amount for t in transactions if t.type == "EXPENSE")
    
    # Group expenses by category
    expenses_by_category = {}
    for t in transactions:
        if t.type == "EXPENSE" and t.category:
            category_name = t.category.name
            expenses_by_category[category_name] = expenses_by_category.get(category_name, 0) + t.amount
    
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": total_income - total_expenses,
        "transactions_count": len(transactions),
        "expenses_by_category": expenses_by_category
    }


@router.get("/expenses-by-category")
def get_expenses_by_category(
    year_month: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Default to current month if not specified
    if not year_month:
        today = date.today()
        year_month = f"{today.year}-{today.month:02d}"
    
    year, month = map(int, year_month.split('-'))
    
    # Get expense transactions for specified month grouped by category
    result = db.query(
        models.Category.name.label('category_name'),
        func.sum(models.Transaction.amount).label('total_amount')
    ).join(
        models.Transaction, models.Transaction.category_id == models.Category.id
    ).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.type == "EXPENSE",
        models.Transaction.is_deleted == False,
        extract('year', models.Transaction.occurred_on) == year,
        extract('month', models.Transaction.occurred_on) == month
    ).group_by(models.Category.name).all()
    
    # Convert to dictionary
    expenses_by_category = {row.category_name: float(row.total_amount) for row in result}
    
    return expenses_by_category