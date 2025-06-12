from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Dict, List
from datetime import date

from app import models


class BudgetService:
    """Service for budget-related business logic"""
    
    @staticmethod
    def calculate_budget_status(
        db: Session,
        user_id: str,
        year: int,
        month: int,
        budget: models.Budget
    ) -> List[Dict]:
        """Calculate budget status for all categories in a budget"""
        budget_statuses = []
        
        for cat_budget in budget.category_limits:
            # Calculate spent amount for this category in this period
            spent_amount = db.query(func.sum(models.Transaction.amount)).filter(
                models.Transaction.user_id == user_id,
                models.Transaction.category_id == cat_budget.category_id,
                models.Transaction.type == "EXPENSE",
                models.Transaction.is_deleted == False,
                extract('year', models.Transaction.occurred_on) == year,
                extract('month', models.Transaction.occurred_on) == month
            ).scalar() or 0.0
            
            remaining = cat_budget.budget_amount - spent_amount
            percentage_used = (spent_amount / cat_budget.budget_amount * 100) if cat_budget.budget_amount > 0 else 0
            
            # Determine status
            if percentage_used >= 100:
                status = "over_budget"
            elif percentage_used >= 80:
                status = "near_limit"
            else:
                status = "under_budget"
            
            budget_statuses.append({
                "budget_id": cat_budget.category_id,
                "budget_name": cat_budget.category.name,
                "budget_amount": cat_budget.budget_amount,
                "spent_amount": spent_amount,
                "remaining_amount": remaining,
                "percentage_used": percentage_used,
                "status": status
            })
        
        return budget_statuses
    
    @staticmethod
    def calculate_overall_budget_status(budget_statuses: List[Dict]) -> str:
        """Calculate overall budget status from individual category statuses"""
        if not budget_statuses:
            return "no_budgets"
        
        total_budgeted = sum(b["budget_amount"] for b in budget_statuses)
        total_spent = sum(b["spent_amount"] for b in budget_statuses)
        
        overall_percentage = (total_spent / total_budgeted * 100) if total_budgeted > 0 else 0
        
        if overall_percentage >= 100:
            return "over_budget"
        elif overall_percentage >= 80:
            return "near_limit"
        else:
            return "under_budget"
    
    @staticmethod
    def get_expenses_by_category(
        db: Session,
        user_id: str,
        year: int,
        month: int
    ) -> Dict[str, float]:
        """Get expenses grouped by category for a specific month"""
        result = db.query(
            models.Category.name.label('category_name'),
            func.sum(models.Transaction.amount).label('total_amount')
        ).join(
            models.Transaction, models.Transaction.category_id == models.Category.id
        ).filter(
            models.Transaction.user_id == user_id,
            models.Transaction.type == "EXPENSE",
            models.Transaction.is_deleted == False,
            extract('year', models.Transaction.occurred_on) == year,
            extract('month', models.Transaction.occurred_on) == month
        ).group_by(models.Category.name).all()
        
        return {row.category_name: float(row.total_amount) for row in result}