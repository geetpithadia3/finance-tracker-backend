from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from datetime import date, datetime, timezone
import logging

from app.database import get_db
from app import models, schemas, auth
from app.routers.budgets import get_spending_for_category, calculate_month_dates

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def calculate_financial_status(budget_categories, total_expenses, total_budget_amount, days_in_month, current_day):
    """
    Calculate comprehensive financial status using multiple factors
    """
    if not budget_categories or total_budget_amount == 0:
        return {
            "status": "No Budget",
            "score": 0,
            "details": "No budget data available"
        }
    
    # Factor 1: Overall Budget Utilization (0-100 points)
    budget_utilization = (total_expenses / total_budget_amount * 100) if total_budget_amount > 0 else 0
    budget_score = max(0, 100 - budget_utilization)  # Higher score for lower utilization
    
    # Factor 2: Time-based Spending Velocity (0-100 points)
    days_remaining = days_in_month - current_day
    if days_remaining <= 0:
        velocity_score = 0
    else:
        daily_budget = total_budget_amount / days_in_month
        daily_spent = total_expenses / current_day if current_day > 0 else 0
        velocity_ratio = daily_spent / daily_budget if daily_budget > 0 else 1
        velocity_score = max(0, 100 - (velocity_ratio * 100))
    
    # Factor 3: Category Health (0-100 points)
    category_scores = []
    critical_overages = 0
    warning_categories = 0
    
    for cat in budget_categories:
        if cat['effective_budget'] > 0:
            percentage_used = cat['percentage_used']
            
            if percentage_used >= 100:
                category_scores.append(0)  # Over budget
                critical_overages += 1
            elif percentage_used >= 90:
                category_scores.append(20)  # Warning
                warning_categories += 1
            elif percentage_used >= 80:
                category_scores.append(60)  # Caution
            elif percentage_used >= 70:
                category_scores.append(80)  # Good
            else:
                category_scores.append(100)  # Excellent
    
    category_score = sum(category_scores) / len(category_scores) if category_scores else 0
    
    # Factor 4: Emergency Fund Check (0-50 points)
    # This would need savings data, but for now we'll use a simplified approach
    emergency_score = 50  # Placeholder - could be enhanced with savings rate analysis
    
    # Calculate weighted final score
    final_score = (
        budget_score * 0.3 +      # 30% weight
        velocity_score * 0.25 +   # 25% weight
        category_score * 0.35 +   # 35% weight
        emergency_score * 0.1     # 10% weight
    )
    
    # Determine status based on final score
    if final_score >= 85:
        status = "Excellent"
        status_color = "green"
    elif final_score >= 70:
        status = "On Track"
        status_color = "blue"
    elif final_score >= 50:
        status = "Caution"
        status_color = "yellow"
    elif final_score >= 30:
        status = "Warning"
        status_color = "orange"
    else:
        status = "Critical"
        status_color = "red"
    
    # Generate detailed insights
    details = []
    if critical_overages > 0:
        details.append(f"{critical_overages} category{'s' if critical_overages > 1 else ''} over budget")
    if warning_categories > 0:
        details.append(f"{warning_categories} category{'s' if warning_categories > 1 else ''} near limit")
    if budget_utilization > 100:
        details.append("Overall spending exceeds budget")
    elif budget_utilization > 90:
        details.append("Approaching budget limit")
    
    if not details:
        if final_score >= 85:
            details.append("All categories within healthy limits")
        else:
            details.append("Monitor spending patterns")
    
    return {
        "status": status,
        "score": round(final_score, 1),
        "status_color": status_color,
        "budget_utilization": round(budget_utilization, 1),
        "velocity_score": round(velocity_score, 1),
        "category_score": round(category_score, 1),
        "critical_overages": critical_overages,
        "warning_categories": warning_categories,
        "details": details
    }


@router.get("")
def get_dashboard(
    year_month: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    logger = logging.getLogger("dashboard-debug")
    # Default to current month if not specified
    if not year_month:
        today = date.today()
        year_month = f"{today.year}-{today.month:02d}"
    
    year, month = map(int, year_month.split('-'))
    
    logger.info(f"Dashboard request for user_id={current_user.id}, year_month={year_month}")
    
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
    
    # Calculate transaction totals
    total_income = sum(abs(t.amount) for t in income)
    total_savings = sum(abs(t.amount) for t in savings)
    total_expenses = sum(t.personal_share or 0 for t in expenses)
    
    # Calculate expenses by category
    expenses_by_category = {}
    for t in expenses:
        category_name = t.category.name if t.category else "Uncategorized"
        expenses_by_category[category_name] = expenses_by_category.get(category_name, 0) + (t.personal_share or 0)
    
    # Get budget data for this period
    budget = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.year_month == year_month
    ).first()
    
    budget_categories = []
    total_budget_expenses = 0
    total_budget_amount = 0
    
    if budget:
        for cat_budget in budget.category_limits:
            # Calculate spent amount for this category in this period
            start_date, end_date = calculate_month_dates(year_month)
            spent = get_spending_for_category(
                db, 
                current_user.id, 
                cat_budget.category_id, 
                start_date,
                end_date
            )
            
            # Calculate rollover amount if enabled for this category
            rollover_amount = 0
            if cat_budget.rollover_enabled:
                # Get previous month's budget for this category
                prev_year, prev_month = year, month - 1
                if prev_month == 0:
                    prev_month = 12
                    prev_year -= 1
                prev_year_month = f"{prev_year}-{prev_month:02d}"
                
                prev_budget = db.query(models.Budget).filter(
                    models.Budget.user_id == current_user.id,
                    models.Budget.year_month == prev_year_month
                ).first()
                
                if prev_budget:
                    prev_cat_budget = next((cl for cl in prev_budget.category_limits if cl.category_id == cat_budget.category_id), None)
                    if prev_cat_budget:
                        prev_start_date, prev_end_date = calculate_month_dates(prev_year_month)
                        prev_spent = get_spending_for_category(
                            db, 
                            current_user.id, 
                            cat_budget.category_id, 
                            prev_start_date,
                            prev_end_date
                        )
                        rollover_amount = max(0, prev_cat_budget.budget_amount - prev_spent)
            
            effective_budget = cat_budget.budget_amount + rollover_amount
            remaining_amount = effective_budget - spent
            
            # Determine status
            percentage_used = (spent / effective_budget * 100) if effective_budget > 0 else 0
            if percentage_used >= 100:
                status = "over"
            elif percentage_used >= 80:
                status = "warning"
            else:
                status = "good"
            
            budget_categories.append({
                "category_name": cat_budget.category.name,
                "budget_amount": float(cat_budget.budget_amount),
                "spent_amount": float(spent),
                "remaining_amount": float(remaining_amount),
                "percentage_used": float(percentage_used),
                "status": status,
                "rollover_amount": float(rollover_amount),
                "effective_budget": float(effective_budget),
                "rollover_enabled": cat_budget.rollover_enabled
            })
            
            total_budget_expenses += spent
            total_budget_amount += effective_budget
    
    # Get spending trends for the last 6 months
    spending_trends = []
    for i in range(5, -1, -1):  # Last 6 months
        trend_year, trend_month = year, month - i
        if trend_month <= 0:
            trend_month += 12
            trend_year -= 1
        
        trend_year_month = f"{trend_year}-{trend_month:02d}"
        
        # Get transactions for this month
        trend_transactions = db.query(models.Transaction).filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.is_deleted == False,
            extract('year', models.Transaction.occurred_on) == trend_year,
            extract('month', models.Transaction.occurred_on) == trend_month
        ).all()
        
        # Calculate totals for this month
        trend_income = sum(abs(t.amount) for t in trend_transactions 
                          if (t.type == "CREDIT" and t.amount > 0) or 
                          (t.category and t.category.name in income_category_names))
        trend_expenses = sum(t.personal_share or 0 for t in trend_transactions 
                           if t.type == "DEBIT" and (not t.category or 
                           (t.category.name != 'Transfer' and t.category.name != 'Savings')))
        trend_savings = sum(abs(t.amount) for t in trend_transactions 
                           if t.category and t.category.name == 'Savings')
        
        spending_trends.append({
            "month": datetime(trend_year, trend_month, 1, tzinfo=timezone.utc).strftime("%b"),
            "income": float(trend_income),
            "expenses": float(trend_expenses),
            "savings": float(trend_savings)
        })
    
    # Get project budgets
    current_date = datetime.now(timezone.utc)
    
    # For database queries, we need to handle timezone-naive dates from the database
    # We'll filter in Python after fetching to ensure proper timezone comparison
    all_projects = db.query(models.ProjectBudget).filter(
        models.ProjectBudget.user_id == current_user.id
    ).all()
    
    active_projects = []
    for project in all_projects:
        # Ensure project dates are timezone-aware
        project_start = project.start_date
        project_end = project.end_date
        
        if project_start.tzinfo is None:
            project_start = project_start.replace(tzinfo=timezone.utc)
        if project_end.tzinfo is None:
            project_end = project_end.replace(tzinfo=timezone.utc)
        
        if project_start <= current_date <= project_end:
            active_projects.append(project)
    
    project_budgets = []
    for project in active_projects:
        # Calculate project progress
        project_transactions = db.query(models.Transaction).filter(
            models.Transaction.user_id == current_user.id,
            models.Transaction.is_deleted == False,
            models.Transaction.occurred_on >= project.start_date,
            models.Transaction.occurred_on <= project.end_date
        ).all()
        
        total_spent = sum(t.personal_share or 0 for t in project_transactions if t.type == "DEBIT")
        progress_percentage = (total_spent / project.total_amount * 100) if project.total_amount > 0 else 0
        
        project_budgets.append({
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "start_date": project.start_date.isoformat(),
            "end_date": project.end_date.isoformat(),
            "total_amount": float(project.total_amount),
            "total_spent": float(total_spent),
            "remaining_amount": float(project.total_amount - total_spent),
            "progress_percentage": float(progress_percentage)
        })
    
    # Calculate additional metrics
    net_flow = total_income - total_expenses
    savings_rate = (total_savings / total_income * 100) if total_income > 0 else 0
    budget_utilization = (total_budget_expenses / total_budget_amount * 100) if total_budget_amount > 0 else 0
    
    # Get category count
    category_count = len(set(t.category.name for t in all_transactions if t.category))
    
    # Calculate average daily spending
    days_in_month = (datetime(year, month + 1, 1, tzinfo=timezone.utc) - datetime(year, month, 1, tzinfo=timezone.utc)).days if month < 12 else (datetime(year + 1, 1, 1, tzinfo=timezone.utc) - datetime(year, month, 1, tzinfo=timezone.utc)).days
    avg_daily_spending = total_expenses / days_in_month if days_in_month > 0 else 0
    
    # Calculate current day of month
    current_day = min(datetime.now(timezone.utc).day, days_in_month) if datetime.now(timezone.utc).year == year and datetime.now(timezone.utc).month == month else days_in_month
    
    # Calculate comprehensive financial status
    financial_status = calculate_financial_status(
        budget_categories, 
        total_expenses, 
        total_budget_amount, 
        days_in_month, 
        current_day
    )
    
    return {
        # Transaction data
        "total_income": float(total_income),
        "total_savings": float(total_savings),
        "total_expenses": float(total_expenses),
        "expenses_by_category": expenses_by_category,
        
        # Budget data
        "budget_categories": budget_categories,
        "total_budget_expenses": float(total_budget_expenses),
        "total_budget_amount": float(total_budget_amount),
        
        # Trends data
        "spending_trends": spending_trends,
        
        # Project budgets
        "project_budgets": project_budgets,
        
        # Additional metrics
        "net_flow": float(net_flow),
        "savings_rate": float(savings_rate),
        "budget_utilization": float(budget_utilization),
        "category_count": category_count,
        "avg_daily_spending": float(avg_daily_spending),
        
        # Financial status
        "financial_status": financial_status,
        
        # Metadata
        "year_month": year_month,
        "days_in_month": days_in_month,
        "current_day": current_day
    }


