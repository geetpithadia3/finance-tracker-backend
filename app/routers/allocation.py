from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from typing import List

from app.database import get_db
from app import models, schemas, auth
from app.routers.recurring_transactions import calculate_next_due_date_enhanced

router = APIRouter(prefix="/allocation", tags=["allocation"])


def calculate_paycheck_dates_for_month(income_recurring: models.RecurringTransaction, year: int, month: int) -> List[datetime]:
    """Calculate all paycheck dates for a given month based on recurring income pattern, preserving cadence across months."""
    paycheck_dates = []
    freq = income_recurring.frequency.value if hasattr(income_recurring.frequency, 'value') else income_recurring.frequency
    start_date = income_recurring.start_date
    
    # Ensure start_date is timezone-aware
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    
    # Determine the interval for the frequency
    if freq == "DAILY":
        delta = timedelta(days=1)
    elif freq == "WEEKLY":
        delta = timedelta(weeks=1)
    elif freq == "BIWEEKLY":
        delta = timedelta(weeks=2)
    elif freq == "FOUR_WEEKLY":
        delta = timedelta(weeks=4)
    elif freq == "MONTHLY":
        delta = None  # handled separately
    elif freq == "YEARLY":
        delta = None  # handled separately
    else:
        delta = None
    
    # Calculate the range for the target month
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)
    else:
        month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc) - timedelta(seconds=1)

    # For daily/weekly/biweekly/four-weekly, preserve cadence from start_date
    if delta is not None:
        # Find the first occurrence on or before month_start
        current = start_date
        while current < month_start:
            current += delta
        # If we overshot, step back one interval
        if current > month_start:
            current -= delta
        # Now, iterate forward and collect all paychecks in the month
        while current <= month_end:
            if current >= month_start:
                paycheck_dates.append(current)
            current += delta
    elif freq == "MONTHLY":
        # For monthly, step forward by months from start_date
        current = start_date
        while current < month_start:
            current += relativedelta(months=1)
        while current <= month_end:
            if current >= month_start:
                paycheck_dates.append(current)
            current += relativedelta(months=1)
    elif freq == "YEARLY":
        # For yearly, step forward by years from start_date
        current = start_date
        while current < month_start:
            current += relativedelta(years=1)
        while current <= month_end:
            if current >= month_start:
                paycheck_dates.append(current)
            current += relativedelta(years=1)
    return paycheck_dates


def calculate_expense_dates_between_paychecks(
    expense_recurring: models.RecurringTransaction, 
    paycheck_date: datetime, 
    next_paycheck_date: datetime = None
) -> List[datetime]:
    """Calculate all expense due dates between two paycheck dates"""
    expense_dates = []
    
    # Ensure all dates are timezone-aware
    if paycheck_date.tzinfo is None:
        paycheck_date = paycheck_date.replace(tzinfo=timezone.utc)
    
    # If no next paycheck date, look 30 days ahead
    if next_paycheck_date is None:
        next_paycheck_date = paycheck_date + timedelta(days=30)
    elif next_paycheck_date.tzinfo is None:
        next_paycheck_date = next_paycheck_date.replace(tzinfo=timezone.utc)
    
    # Ensure expense due date is timezone-aware
    expense_due_date = expense_recurring.next_due_date
    if expense_due_date.tzinfo is None:
        expense_due_date = expense_due_date.replace(tzinfo=timezone.utc)
    
    # Start from the current expense's next due date or the paycheck date, whichever is later
    current_date = max(expense_due_date, paycheck_date)
    
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
        return schemas.AllocationResponse(
            paychecks=[],
            month=year_month,
            income=0.0,
            total_expenses=0.0,
            savings=0.0
        )
    
    paychecks = []

    # For each recurring income source, calculate paycheck schedule for the month
    for income_recurring in recurring_income:
        paycheck_dates = calculate_paycheck_dates_for_month(income_recurring, year, month)
        print(f"DEBUG: Income '{income_recurring.description}' has {len(paycheck_dates)} paychecks in {year_month}")
        if not paycheck_dates:
            continue
        # Build the full rolling range: from first paycheck to the last next-paycheck date
        periods = []
        for i, paycheck_date in enumerate(paycheck_dates):
            if i + 1 < len(paycheck_dates):
                next_paycheck_date = paycheck_dates[i + 1]
            else:
                # Find the next paycheck date after the last one
                freq = income_recurring.frequency.value if hasattr(income_recurring.frequency, 'value') else income_recurring.frequency
                current = paycheck_date
                if freq == "DAILY":
                    next_paycheck_date = current + timedelta(days=1)
                elif freq == "WEEKLY":
                    next_paycheck_date = current + timedelta(weeks=1)
                elif freq == "BIWEEKLY":
                    next_paycheck_date = current + timedelta(weeks=2)
                elif freq == "FOUR_WEEKLY":
                    next_paycheck_date = current + timedelta(weeks=4)
                elif freq == "MONTHLY":
                    next_paycheck_date = current + relativedelta(months=1)
                elif freq == "YEARLY":
                    next_paycheck_date = current + relativedelta(years=1)
                else:
                    next_paycheck_date = None
            periods.append((paycheck_date, next_paycheck_date))
        # Determine the full range for expense occurrences
        full_range_start = periods[0][0]
        full_range_end = periods[-1][1]
        # Generate all expense occurrences for the full range
        def generate_expense_occurrences_rolling(expense_recurring, range_start, range_end):
            freq = expense_recurring.frequency.value if hasattr(expense_recurring.frequency, 'value') else expense_recurring.frequency
            occurrences = []
            current = expense_recurring.start_date
            
            # Ensure current date is timezone-aware
            if current.tzinfo is None:
                current = current.replace(tzinfo=timezone.utc)
            
            # Find the first occurrence on or after range_start
            while current < range_start:
                if freq == "DAILY":
                    current += timedelta(days=1)
                elif freq == "WEEKLY":
                    current += timedelta(weeks=1)
                elif freq == "BIWEEKLY":
                    current += timedelta(weeks=2)
                elif freq == "FOUR_WEEKLY":
                    current += timedelta(weeks=4)
                elif freq == "MONTHLY":
                    current += relativedelta(months=1)
                elif freq == "YEARLY":
                    current += relativedelta(years=1)
                else:
                    break
            # Now, collect all occurrences in the range
            while current < range_end:
                if current >= range_start:
                    occurrences.append(current)
                if freq == "DAILY":
                    current += timedelta(days=1)
                elif freq == "WEEKLY":
                    current += timedelta(weeks=1)
                elif freq == "BIWEEKLY":
                    current += timedelta(weeks=2)
                elif freq == "FOUR_WEEKLY":
                    current += timedelta(weeks=4)
                elif freq == "MONTHLY":
                    current += relativedelta(months=1)
                elif freq == "YEARLY":
                    current += relativedelta(years=1)
                else:
                    break
            return occurrences
        # Precompute all expense occurrences for each recurring expense for the full rolling range
        expense_occurrences = {}
        for expense_recurring in recurring_expenses:
            expense_occurrences[expense_recurring.id] = generate_expense_occurrences_rolling(
                expense_recurring, full_range_start, full_range_end)
        # Now, for each paycheck period, allocate expenses
        for (paycheck_date, next_paycheck_date) in periods:
            expenses_in_period = []
            total_allocation = 0.0
            for expense_recurring in recurring_expenses:
                for expense_date in expense_occurrences[expense_recurring.id]:
                    if paycheck_date <= expense_date < next_paycheck_date:
                        upcoming_expense = schemas.UpcomingExpense(
                            id=f"{expense_recurring.id}-{expense_date.isoformat()}",
                            description=expense_recurring.description,
                            amount=abs(expense_recurring.amount),
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
            freq_value = income_recurring.frequency.value if hasattr(income_recurring.frequency, 'value') else income_recurring.frequency
            paycheck = schemas.PaycheckAllocation(
                id=f"{income_recurring.id}-{paycheck_date.isoformat()}",
                amount=abs(income_recurring.amount),
                date=paycheck_date,
                source=income_recurring.description,
                frequency=freq_value,
                expenses=expenses_in_period,
                total_allocation_amount=total_allocation,
                remaining_amount=abs(income_recurring.amount) - total_allocation,
                next_paycheck_date=next_paycheck_date
            )
            paychecks.append(paycheck)
            print(f"DEBUG: Paycheck on {paycheck_date} covers {len(expenses_in_period)} expenses totaling ${total_allocation}")
    
    print(f"DEBUG: Returning {len(paychecks)} paychecks for {year_month}")
    return schemas.AllocationResponse(
        paychecks=paychecks,
        month=year_month,
        income=0.0,
        total_expenses=0.0,
        savings=0.0
    )