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
    
    # Separate transactions by category-based logic
    # Income: transactions in income categories OR positive CREDIT transactions that look like income
    income_category_names = ['Income', 'Side Income', 'Investment Income', 'Other Income', 'Salary']
    income_keywords = ['payroll', 'salary', 'wage', 'income', 'deposit', 'refund']
    
    income = []
    for t in all_transactions:
        # Include if categorized as income
        if t.category and t.category.name in income_category_names:
            income.append(t)
        # Include positive CREDIT transactions with income-related descriptions
        elif (t.type == "CREDIT" and t.amount > 0 and 
              any(keyword in t.description.lower() for keyword in income_keywords)):
            income.append(t)
    
    # Savings: transactions categorized as "Savings"
    savings = [t for t in all_transactions if t.category and t.category.name == 'Savings']
    
    # Expenses: DEBIT transactions that are NOT categorized as "Transfer"
    expenses = [t for t in all_transactions 
               if t.type == "DEBIT" and (not t.category or (t.category.name != 'Transfer' and t.category.name != 'Savings'))]
    
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
                models.Transaction.type == "DEBIT",
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
        # For CREDIT transactions, convert negative amounts to positive
        amount = abs(t.amount) if t.type == "CREDIT" and t.amount < 0 else t.amount
        personal_share = abs(t.personal_share) if t.type == "CREDIT" and t.personal_share < 0 else t.personal_share
        
        return {
            "id": t.id,
            "description": t.description,
            "amount": amount,
            "occurred_on": t.occurred_on,
            "date": t.occurred_on,  # Add date field for backward compatibility
            "category": t.category.name if t.category else "Uncategorized",
            "personal_share": personal_share,
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
    # Expenses are DEBIT transactions that are NOT categorized as "Transfer"
    result = db.query(
        models.Category.name.label('category_name'),
        func.sum(models.Transaction.amount).label('total_amount')
    ).join(
        models.Transaction, models.Transaction.category_id == models.Category.id
    ).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.type == "DEBIT",
        models.Transaction.is_deleted == False,
        models.Category.name != "Transfer",
        extract('year', models.Transaction.occurred_on) == year,
        extract('month', models.Transaction.occurred_on) == month
    ).group_by(models.Category.name).all()
    
    # Convert to dictionary
    expenses_by_category = {row.category_name: float(row.total_amount) for row in result}
    
    return expenses_by_category