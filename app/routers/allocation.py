from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List

from app.database import get_db
from app import models, schemas, auth
from app.routers.recurring_transactions import calculate_next_due_date_enhanced

router = APIRouter(prefix="/allocation", tags=["allocation"])


def calculate_paycheck_dates_for_month(income_recurring: models.RecurringTransaction, year: int, month: int) -> List[datetime]:
    """Calculate all paycheck dates for a given month based on recurring income pattern"""
    paycheck_dates = []
    
    # Start from the beginning of the month
    month_start = datetime(year, month, 1)
    
    # Calculate the next month for boundary checking
    if month == 12:
        month_end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Start from the recurring transaction's start date or month start, whichever is later
    current_date = max(income_recurring.start_date, month_start)
    
    # If the start date is after this month, no paychecks this month
    if current_date > month_end:
        return []
    
    # Generate paycheck dates based on frequency
    while current_date <= month_end:
        # Check if this date falls within the target month
        if current_date.year == year and current_date.month == month:
            paycheck_dates.append(current_date)
        
        # Calculate next occurrence based on frequency
        if income_recurring.frequency == models.RecurrenceFrequency.DAILY:
            current_date += timedelta(days=1)
        elif income_recurring.frequency == models.RecurrenceFrequency.WEEKLY:
            current_date += timedelta(weeks=1)
        elif income_recurring.frequency == models.RecurrenceFrequency.BIWEEKLY:
            current_date += timedelta(weeks=2)
        elif income_recurring.frequency == models.RecurrenceFrequency.FOUR_WEEKLY:
            current_date += timedelta(weeks=4)
        elif income_recurring.frequency == models.RecurrenceFrequency.MONTHLY:
            current_date += relativedelta(months=1)
        elif income_recurring.frequency == models.RecurrenceFrequency.YEARLY:
            current_date += relativedelta(years=1)
        else:
            # Default to monthly to avoid infinite loop
            current_date += relativedelta(months=1)
        
        # Safety check to avoid infinite loops
        if current_date.year > year + 1:
            break
    
    return paycheck_dates


def calculate_expense_dates_between_paychecks(
    expense_recurring: models.RecurringTransaction, 
    paycheck_date: datetime, 
    next_paycheck_date: datetime = None
) -> List[datetime]:
    """Calculate all expense due dates between two paycheck dates"""
    expense_dates = []
    
    # If no next paycheck date, look 30 days ahead
    if next_paycheck_date is None:
        next_paycheck_date = paycheck_date + timedelta(days=30)
    
    # Start from the current expense's next due date or the paycheck date, whichever is later
    current_date = max(expense_recurring.next_due_date, paycheck_date)
    
    # Generate expense dates until the next paycheck
    while current_date < next_paycheck_date:
        expense_dates.append(current_date)
        
        # Calculate next occurrence based on frequency
        if expense_recurring.frequency == models.RecurrenceFrequency.DAILY:
            current_date += timedelta(days=1)
        elif expense_recurring.frequency == models.RecurrenceFrequency.WEEKLY:
            current_date += timedelta(weeks=1)
        elif expense_recurring.frequency == models.RecurrenceFrequency.BIWEEKLY:
            current_date += timedelta(weeks=2)
        elif expense_recurring.frequency == models.RecurrenceFrequency.FOUR_WEEKLY:
            current_date += timedelta(weeks=4)
        elif expense_recurring.frequency == models.RecurrenceFrequency.MONTHLY:
            current_date += relativedelta(months=1)
        elif expense_recurring.frequency == models.RecurrenceFrequency.YEARLY:
            current_date += relativedelta(years=1)
        else:
            # Default to monthly to avoid infinite loop
            current_date += relativedelta(months=1)
        
        # Safety check - don't look too far ahead
        if current_date.year > paycheck_date.year + 1:
            break
    
    return expense_dates


@router.get("/debug-data")
def debug_allocation_data(
    year_month: str = "2024-12",
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Debug endpoint to see what data exists for allocation"""
    year, month = map(int, year_month.split('-'))
    
    # Get all transactions for the period
    all_transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.is_deleted == False,
        extract('year', models.Transaction.occurred_on) == year,
        extract('month', models.Transaction.occurred_on) == month
    ).all()
    
    # Get all recurring transactions
    recurring_transactions = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.user_id == current_user.id
    ).all()
    
    # Income detection logic
    income_category_names = ['Income', 'Side Income', 'Investment Income', 'Other Income', 'Salary']
    income_keywords = ['payroll', 'salary', 'wage', 'income', 'deposit', 'refund']
    
    transactions_data = []
    income_transactions = []
    
    for t in all_transactions:
        t_data = {
            "id": t.id,
            "type": t.type,
            "amount": t.amount,
            "description": t.description,
            "category": t.category.name if t.category else None,
            "date": t.occurred_on.isoformat(),
            "is_income_by_category": t.category and t.category.name in income_category_names,
            "is_income_by_keywords": (t.type == "CREDIT" and t.amount > 0 and 
                                    any(keyword in t.description.lower() for keyword in income_keywords)),
        }
        transactions_data.append(t_data)
        
        if t_data["is_income_by_category"] or t_data["is_income_by_keywords"]:
            income_transactions.append(t_data)
    
    recurring_data = []
    for rt in recurring_transactions:
        recurring_data.append({
            "id": rt.id,
            "type": rt.type,
            "amount": rt.amount,
            "description": rt.description,
            "frequency": rt.frequency.value,
            "is_active": rt.is_active,
            "category": rt.category.name if rt.category else None
        })
    
    return {
        "year_month": year_month,
        "user_id": current_user.id,
        "total_transactions": len(all_transactions),
        "income_transactions_found": len(income_transactions),
        "total_recurring": len(recurring_transactions),
        "active_recurring": len([rt for rt in recurring_transactions if rt.is_active]),
        "transactions": transactions_data,
        "income_transactions": income_transactions,
        "recurring_transactions": recurring_data,
        "income_categories": income_category_names,
        "income_keywords": income_keywords
    }


@router.get("", response_model=schemas.AllocationResponse)
def get_allocation(
    year_month: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Smart allocation system based on recurring income and expense patterns.
    Calculates which bills are due between paycheck periods for any future month.
    """
    year, month = map(int, year_month.split('-'))
    
    print(f"DEBUG: Allocation request for {year_month} (year={year}, month={month}) by user {current_user.id}")
    
    # Get all active recurring transactions (both income and expenses)
    recurring_transactions = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.user_id == current_user.id,
        models.RecurringTransaction.is_active == True
    ).all()
    
    print(f"DEBUG: Found {len(recurring_transactions)} active recurring transactions")
    
    # Separate recurring income and expenses
    recurring_income = []
    recurring_expenses = []
    
    # Define income categories for classification
    income_category_names = ['Income', 'Side Income', 'Investment Income', 'Other Income', 'Salary', 'Payroll']
    
    for rt in recurring_transactions:
        print(f"DEBUG: Recurring - ID: {rt.id}, Type: {rt.type}, Amount: {rt.amount}, Description: '{rt.description}', Category: {rt.category.name if rt.category else 'None'}")
        
        # Classify as income or expense
        is_income = (
            (rt.type == "CREDIT" and rt.amount > 0) or  # Positive credit transactions
            (rt.category and rt.category.name in income_category_names) or  # Income categories
            ('salary' in rt.description.lower() or 'payroll' in rt.description.lower() or 'income' in rt.description.lower())  # Income keywords
        )
        
        if is_income:
            print(f"DEBUG: Classified as INCOME: {rt.description}")
            recurring_income.append(rt)
        else:
            print(f"DEBUG: Classified as EXPENSE: {rt.description}")
            recurring_expenses.append(rt)
    
    print(f"DEBUG: Found {len(recurring_income)} recurring income, {len(recurring_expenses)} recurring expenses")
    
    if not recurring_income:
        print("DEBUG: No recurring income found, returning empty paychecks")
        return schemas.AllocationResponse(paychecks=[])
    
    paychecks = []
    
    # For each recurring income source, calculate paycheck schedule for the month
    for income_recurring in recurring_income:
        paycheck_dates = calculate_paycheck_dates_for_month(income_recurring, year, month)
        
        print(f"DEBUG: Income '{income_recurring.description}' has {len(paycheck_dates)} paychecks in {year_month}")
        
        for i, paycheck_date in enumerate(paycheck_dates):
            # Calculate next paycheck date (for determining bill coverage period)
            if i + 1 < len(paycheck_dates):
                next_paycheck_date = paycheck_dates[i + 1]
            else:
                # Next paycheck is in the following period
                next_month_dates = calculate_paycheck_dates_for_month(
                    income_recurring, 
                    year if month < 12 else year + 1,
                    month + 1 if month < 12 else 1
                )
                next_paycheck_date = next_month_dates[0] if next_month_dates else None
            
            # Find all expenses due between this paycheck and the next
            expenses_in_period = []
            total_allocation = 0.0
            
            for expense_recurring in recurring_expenses:
                expense_dates = calculate_expense_dates_between_paychecks(
                    expense_recurring, paycheck_date, next_paycheck_date
                )
                
                for expense_date in expense_dates:
                    upcoming_expense = schemas.UpcomingExpense(
                        id=f"{expense_recurring.id}-{expense_date.isoformat()}",
                        description=expense_recurring.description,
                        amount=abs(expense_recurring.amount),  # Make sure it's positive for display
                        due_date=expense_date,
                        category=expense_recurring.category.name if expense_recurring.category else "General",
                        is_recurring=True,
                        variability_factor=0.1 if expense_recurring.is_variable_amount else 0.0,
                        is_variable_amount=expense_recurring.is_variable_amount,
                        estimated_min_amount=expense_recurring.estimated_min_amount,
                        estimated_max_amount=expense_recurring.estimated_max_amount
                    )
                    expenses_in_period.append(upcoming_expense)
                    total_allocation += abs(expense_recurring.amount)
            
            # Create paycheck allocation
            paycheck = schemas.PaycheckAllocation(
                id=f"{income_recurring.id}-{paycheck_date.isoformat()}",
                amount=abs(income_recurring.amount),  # Make sure it's positive
                date=paycheck_date,
                source=income_recurring.description,
                frequency=income_recurring.frequency.value,
                expenses=expenses_in_period,
                total_allocation_amount=total_allocation,
                remaining_amount=abs(income_recurring.amount) - total_allocation,
                next_paycheck_date=next_paycheck_date
            )
            paychecks.append(paycheck)
            
            print(f"DEBUG: Paycheck on {paycheck_date} covers {len(expenses_in_period)} expenses totaling ${total_allocation}")
    
    print(f"DEBUG: Returning {len(paychecks)} paychecks for {year_month}")
    return schemas.AllocationResponse(paychecks=paychecks)