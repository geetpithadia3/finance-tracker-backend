from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
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
    
    # Get all transactions for specified month
    all_transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.is_deleted == False,
        extract('year', models.Transaction.occurred_on) == year,
        extract('month', models.Transaction.occurred_on) == month
    ).all()
    
    # Separate transactions by type
    expenses = [t for t in all_transactions if t.type == "EXPENSE"]
    income = [t for t in all_transactions if t.type == "INCOME"]
    savings = [t for t in all_transactions if t.type == "SAVINGS"]
    
    # Get budget data for this period
    budget = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.year_month == year_month,
        models.Budget.is_active == True
    ).first()
    
    budgets = []
    if budget:
        for cat_budget in budget.category_limits:
            # Calculate spent amount for this category in this period
            spent = db.query(func.sum(models.Transaction.amount)).filter(
                models.Transaction.user_id == current_user.id,
                models.Transaction.category_id == cat_budget.category_id,
                models.Transaction.type == "EXPENSE",
                models.Transaction.is_deleted == False,
                extract('year', models.Transaction.occurred_on) == year,
                extract('month', models.Transaction.occurred_on) == month
            ).scalar() or 0.0
            
            budgets.append({
                "category": cat_budget.category.name,
                "budget_amount": cat_budget.budget_amount,
                "spent": spent
            })
    
    # Convert transactions to response format
    def format_transaction(t):
        return {
            "id": t.id,
            "description": t.description,
            "amount": t.amount,
            "occurred_on": t.occurred_on,
            "category": t.category.name if t.category else "Uncategorized",
            "personal_share": t.personal_share,
            "owed_share": t.owed_share,
            "refunded": t.refunded,
            "type": t.type
        }
    
    return {
        "expenses": [format_transaction(t) for t in expenses],
        "income": [format_transaction(t) for t in income],
        "savings": [format_transaction(t) for t in savings],
        "budgets": budgets
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