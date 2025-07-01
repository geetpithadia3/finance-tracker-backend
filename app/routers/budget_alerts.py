from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract
from typing import List
from datetime import datetime, date, timezone
import calendar

from ..database import get_db
from ..models import Budget, CategoryBudget, Transaction, Category, User, ProjectBudget, ProjectBudgetAllocation
from ..auth import get_current_user

router = APIRouter(prefix="/budget-alerts", tags=["budget-alerts"])

def check_category_alert_thresholds(db: Session, user_id: str, category_budget: CategoryBudget, current_spending: float):
    """
    REQ-006: Check if category has reached alert thresholds (75% or 100%)
    """
    effective_budget = category_budget.budget_amount + category_budget.rollover_amount
    percentage_used = (current_spending / effective_budget * 100) if effective_budget > 0 else 0
    
    alerts = []
    
    # Get category name
    category = db.query(Category).filter(Category.id == category_budget.category_id).first()
    category_name = category.name if category else 'Unknown Category'
    
    if percentage_used >= 100:
        alerts.append({
            'type': 'over_budget',
            'severity': 'high',
            'category_id': category_budget.category_id,
            'category_name': category_name,
            'message': f"{category_name} is over budget",
            'details': {
                'budget_amount': category_budget.budget_amount,
                'rollover_amount': category_budget.rollover_amount,
                'effective_budget': effective_budget,
                'spent_amount': current_spending,
                'percentage_used': percentage_used,
                'overspend_amount': current_spending - effective_budget
            }
        })
    elif percentage_used >= 75:
        alerts.append({
            'type': 'approaching_limit',
            'severity': 'medium',
            'category_id': category_budget.category_id,
            'category_name': category_name,
            'message': f"{category_name} is approaching budget limit",
            'details': {
                'budget_amount': category_budget.budget_amount,
                'rollover_amount': category_budget.rollover_amount,
                'effective_budget': effective_budget,
                'spent_amount': current_spending,
                'percentage_used': percentage_used,
                'remaining_amount': effective_budget - current_spending
            }
        })
    
    return alerts

@router.get("/")
def get_budget_alerts(
    year_month: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    REQ-006: Get budget alerts for current or specified month
    """
    if not year_month:
        # Default to current month
        now = datetime.now(timezone.utc)
        year_month = f"{now.year}-{now.month:02d}"
    
    try:
        year, month = map(int, year_month.split('-'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid year_month format. Use YYYY-MM"
        )
    
    alerts = []
    
    # Check monthly budget alerts
    budget = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.year_month == year_month
        )
    ).first()
    
    if budget:
        for category_limit in budget.category_limits:
            # Calculate current spending
            spent_transactions = db.query(Transaction).filter(
                and_(
                    Transaction.user_id == current_user.id,
                    Transaction.category_id == category_limit.category_id,
                    Transaction.is_deleted == False,
                    extract('year', Transaction.occurred_on) == year,
                    extract('month', Transaction.occurred_on) == month,
                    Transaction.type.in_(['DEBIT', 'EXPENSE'])
                )
            ).all()
            
            current_spending = sum(abs(t.amount) for t in spent_transactions)
            category_alerts = check_category_alert_thresholds(
                db, current_user.id, category_limit, current_spending
            )
            
            for alert in category_alerts:
                alert['budget_type'] = 'monthly'
                alert['budget_id'] = budget.id
                alert['period'] = year_month
                alerts.append(alert)
    
    # Check project budget alerts
    current_date = datetime.now(timezone.utc)
    
    # For database queries, we need to handle timezone-naive dates from the database
    # We'll filter in Python after fetching to ensure proper timezone comparison
    all_projects = db.query(ProjectBudget).filter(
        ProjectBudget.user_id == current_user.id
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
    
    for project in active_projects:
        for allocation in project.category_allocations:
            # Calculate cumulative spending for project period
            spent_transactions = db.query(Transaction).filter(
                and_(
                    Transaction.user_id == current_user.id,
                    Transaction.category_id == allocation.category_id,
                    Transaction.is_deleted == False,
                    Transaction.occurred_on >= project.start_date,
                    Transaction.occurred_on <= project.end_date,
                    Transaction.type.in_(['DEBIT', 'EXPENSE'])
                )
            ).all()
            
            current_spending = sum(abs(t.amount) for t in spent_transactions)
            
            # Check thresholds for project allocation
            percentage_used = (current_spending / allocation.allocated_amount * 100) if allocation.allocated_amount > 0 else 0
            
            # Get category name
            category = db.query(Category).filter(Category.id == allocation.category_id).first()
            category_name = category.name if category else 'Unknown Category'
            
            if percentage_used >= 100:
                alerts.append({
                    'type': 'over_budget',
                    'severity': 'high',
                    'category_id': allocation.category_id,
                    'category_name': category_name,
                    'message': f"{category_name} is over budget in project {project.name}",
                    'budget_type': 'project',
                    'budget_id': project.id,
                    'project_name': project.name,
                    'period': f"{project.start_date.strftime('%Y-%m-%d')} to {project.end_date.strftime('%Y-%m-%d')}",
                    'details': {
                        'allocated_amount': allocation.allocated_amount,
                        'spent_amount': current_spending,
                        'percentage_used': percentage_used,
                        'overspend_amount': current_spending - allocation.allocated_amount
                    }
                })
            elif percentage_used >= 75:
                alerts.append({
                    'type': 'approaching_limit',
                    'severity': 'medium',
                    'category_id': allocation.category_id,
                    'category_name': category_name,
                    'message': f"{category_name} is approaching budget limit in project {project.name}",
                    'budget_type': 'project',
                    'budget_id': project.id,
                    'project_name': project.name,
                    'period': f"{project.start_date.strftime('%Y-%m-%d')} to {project.end_date.strftime('%Y-%m-%d')}",
                    'details': {
                        'allocated_amount': allocation.allocated_amount,
                        'spent_amount': current_spending,
                        'percentage_used': percentage_used,
                        'remaining_amount': allocation.allocated_amount - current_spending
                    }
                })
    
    # Sort alerts by severity (high first, then medium)
    alerts.sort(key=lambda x: 0 if x['severity'] == 'high' else 1)
    
    return {
        'year_month': year_month,
        'alert_count': len(alerts),
        'high_priority_count': len([a for a in alerts if a['severity'] == 'high']),
        'medium_priority_count': len([a for a in alerts if a['severity'] == 'medium']),
        'alerts': alerts
    }

@router.get("/summary")
def get_budget_alert_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    REQ-006: Get monthly summary report of budget performance
    """
    now = datetime.now(timezone.utc)
    current_year_month = f"{now.year}-{now.month:02d}"
    
    # Get alerts for current month
    alerts_response = get_budget_alerts(current_year_month, db, current_user)
    alerts = alerts_response['alerts']
    
    # Calculate summary statistics
    total_categories_tracked = 0
    categories_over_budget = 0
    categories_at_warning = 0
    categories_on_track = 0
    
    # Track unique categories
    tracked_categories = set()
    
    # Check monthly budget
    budget = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.year_month == current_year_month
        )
    ).first()
    
    if budget:
        for category_limit in budget.category_limits:
            tracked_categories.add(category_limit.category_id)
            
            # Find alerts for this category
            category_alerts = [a for a in alerts if a['category_id'] == category_limit.category_id and a['budget_type'] == 'monthly']
            
            if any(a['type'] == 'over_budget' for a in category_alerts):
                categories_over_budget += 1
            elif any(a['type'] == 'approaching_limit' for a in category_alerts):
                categories_at_warning += 1
            else:
                categories_on_track += 1
    
    # Check active project budgets
    current_date = datetime.now(timezone.utc)
    
    # For database queries, we need to handle timezone-naive dates from the database
    # We'll filter in Python after fetching to ensure proper timezone comparison
    all_projects = db.query(ProjectBudget).filter(
        ProjectBudget.user_id == current_user.id
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
    
    project_categories = set()
    for project in active_projects:
        for allocation in project.category_allocations:
            if allocation.category_id not in tracked_categories:
                project_categories.add(allocation.category_id)
                
                # Find alerts for this category in projects
                category_alerts = [a for a in alerts if a['category_id'] == allocation.category_id and a['budget_type'] == 'project']
                
                if any(a['type'] == 'over_budget' for a in category_alerts):
                    categories_over_budget += 1
                elif any(a['type'] == 'approaching_limit' for a in category_alerts):
                    categories_at_warning += 1
                else:
                    categories_on_track += 1
    
    total_categories_tracked = len(tracked_categories) + len(project_categories)
    
    return {
        'period': current_year_month,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'summary': {
            'total_categories_tracked': total_categories_tracked,
            'categories_on_track': categories_on_track,
            'categories_at_warning': categories_at_warning,
            'categories_over_budget': categories_over_budget,
            'overall_health': 'good' if categories_over_budget == 0 and categories_at_warning <= 1 else 'warning' if categories_over_budget <= 1 else 'poor'
        },
        'alerts': alerts[:5],  # Top 5 most critical alerts
        'recommendations': [
            "Review spending in over-budget categories" if categories_over_budget > 0 else None,
            "Monitor categories approaching limits" if categories_at_warning > 0 else None,
            "Consider adjusting budget allocations for next month" if categories_over_budget > 2 else None
        ]
    }