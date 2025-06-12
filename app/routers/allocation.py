from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime

from app.database import get_db
from app import models, schemas, auth
from app.routers.recurring_transactions import calculate_next_due_date

router = APIRouter(prefix="/allocation", tags=["allocation"])


@router.get("", response_model=schemas.AllocationResponse)
def get_allocation(
    year_month: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Smart allocation system that analyzes income patterns and upcoming expenses
    to provide optimized budget allocation recommendations.
    """
    year, month = map(int, year_month.split('-'))
    
    # Get income transactions (paychecks) for this period
    income_transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.type == "INCOME",
        models.Transaction.is_deleted == False,
        extract('year', models.Transaction.occurred_on) == year,
        extract('month', models.Transaction.occurred_on) == month
    ).all()
    
    if not income_transactions:
        return schemas.AllocationResponse(paychecks=[])
    
    # Get active recurring transactions as upcoming expenses
    recurring_transactions = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.user_id == current_user.id,
        models.RecurringTransaction.is_active == True
    ).all()
    
    # Get budget for this period to understand planned expenses
    budget = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.year_month == year_month,
        models.Budget.is_active == True
    ).first()
    
    paychecks = []
    
    for income in income_transactions:
        # Predict upcoming expenses based on recurring transactions and budget
        upcoming_expenses = []
        total_allocation = 0.0
        
        for recurring in recurring_transactions:
            if recurring.type == "EXPENSE":
                # Calculate next due date (simplified)
                next_due = calculate_next_due_date(recurring.start_date, recurring.frequency)
                
                # Determine variability factor based on historical data
                variability_factor = 0.1 if recurring.is_variable_amount else 0.0
                
                upcoming_expense = schemas.UpcomingExpense(
                    id=recurring.id,
                    description=recurring.description,
                    amount=recurring.amount,
                    due_date=next_due,
                    category=recurring.category.name if recurring.category else "General",
                    is_recurring=True,
                    variability_factor=variability_factor,
                    is_variable_amount=recurring.is_variable_amount,
                    estimated_min_amount=recurring.estimated_min_amount,
                    estimated_max_amount=recurring.estimated_max_amount
                )
                upcoming_expenses.append(upcoming_expense)
                total_allocation += recurring.amount
        
        # Add budget-based expenses (non-recurring planned expenses)
        if budget:
            for cat_budget in budget.category_limits:
                # Estimate remaining budget allocation needed for the month
                current_spent = db.query(func.sum(models.Transaction.amount)).filter(
                    models.Transaction.user_id == current_user.id,
                    models.Transaction.category_id == cat_budget.category_id,
                    models.Transaction.type == "EXPENSE",
                    models.Transaction.is_deleted == False,
                    extract('year', models.Transaction.occurred_on) == year,
                    extract('month', models.Transaction.occurred_on) == month
                ).scalar() or 0.0
                
                remaining_budget = cat_budget.budget_amount - current_spent
                if remaining_budget > 0:
                    # Add as upcoming planned expense
                    upcoming_expense = schemas.UpcomingExpense(
                        id=f"budget-{cat_budget.category_id}",
                        description=f"Remaining {cat_budget.category.name} budget",
                        amount=remaining_budget,
                        due_date=datetime(year, month, 28),  # End of month
                        category=cat_budget.category.name,
                        is_recurring=False,
                        variability_factor=0.3  # Budget items have moderate variability
                    )
                    upcoming_expenses.append(upcoming_expense)
                    total_allocation += remaining_budget
        
        # Determine paycheck frequency based on historical data (simplified)
        frequency = "MONTHLY"  # Default assumption
        
        # Calculate next paycheck date (simplified - assume monthly)
        if month == 12:
            next_paycheck_date = datetime(year + 1, 1, income.occurred_on.day)
        else:
            next_paycheck_date = datetime(year, month + 1, income.occurred_on.day)
        
        paycheck = schemas.PaycheckAllocation(
            id=income.id,
            amount=income.amount,
            date=income.occurred_on,
            source=income.description,
            frequency=frequency,
            expenses=upcoming_expenses,
            total_allocation_amount=total_allocation,
            remaining_amount=income.amount - total_allocation,
            next_paycheck_date=next_paycheck_date
        )
        paychecks.append(paycheck)
    
    return schemas.AllocationResponse(paychecks=paychecks)