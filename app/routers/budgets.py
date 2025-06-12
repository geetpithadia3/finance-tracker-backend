from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List
from datetime import date
import io
import csv

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/budgets", tags=["budgets"])

@router.post("", response_model=schemas.BudgetResponse)
def create_budget(
    budget_request: schemas.BudgetCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Check if budget already exists for this year_month
    existing_budget = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.year_month == budget_request.year_month,
        models.Budget.is_active == True
    ).first()
    
    if existing_budget:
        raise HTTPException(status_code=400, detail="Budget already exists for this period")
    
    # Verify all categories belong to user
    category_ids = [limit.category_id for limit in budget_request.category_limits]
    categories = db.query(models.Category).filter(
        models.Category.id.in_(category_ids),
        models.Category.user_id == current_user.id
    ).all()
    
    if len(categories) != len(category_ids):
        raise HTTPException(status_code=404, detail="One or more categories not found")
    
    # Create budget
    db_budget = models.Budget(
        user_id=current_user.id,
        year_month=budget_request.year_month
    )
    db.add(db_budget)
    db.flush()  # Get the budget ID
    
    # Create category limits
    for limit in budget_request.category_limits:
        db_category_budget = models.CategoryBudget(
            budget_id=db_budget.id,
            category_id=limit.category_id,
            budget_amount=limit.budget_amount
        )
        db.add(db_category_budget)
    
    db.commit()
    db.refresh(db_budget)
    
    # Build response
    category_limits_response = []
    for cat_budget in db_budget.category_limits:
        category = next(cat for cat in categories if cat.id == cat_budget.category_id)
        category_limits_response.append(schemas.CategoryBudgetResponse(
            category_id=cat_budget.category_id,
            category_name=category.name,
            budget_amount=cat_budget.budget_amount
        ))
    
    return schemas.BudgetResponse(
        id=db_budget.id,
        year_month=db_budget.year_month,
        category_limits=category_limits_response
    )


@router.get("", response_model=schemas.BudgetDetailsResponse)
def get_budget_details(
    year_month: str = None,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Default to current month if not specified
    if not year_month:
        today = date.today()
        year_month = f"{today.year}-{today.month:02d}"
    
    # Get budget for specified period
    budget = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.year_month == year_month,
        models.Budget.is_active == True
    ).first()
    
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found for this period")
    
    # Parse year and month from year_month string
    year, month = map(int, year_month.split('-'))
    
    # Get spending for each category in this period
    category_details = []
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
        
        category_details.append(schemas.CategoryBudgetDetailsResponse(
            category_id=cat_budget.category_id,
            category_name=cat_budget.category.name,
            budget_amount=cat_budget.budget_amount,
            spent=spent
        ))
    
    return schemas.BudgetDetailsResponse(
        id=budget.id,
        year_month=budget.year_month,
        categories=category_details
    )


@router.get("/comparison/monthly", response_model=schemas.BudgetComparison)
def get_monthly_budget_comparison(
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
    
    year_month = f"{year}-{month:02d}"
    
    # Get budget for this period
    budget = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.year_month == year_month,
        models.Budget.is_active == True
    ).first()
    
    if not budget:
        return schemas.BudgetComparison(
            period=year_month,
            budgets=[],
            total_budgeted=0.0,
            total_spent=0.0,
            overall_status="no_budgets"
        )
    
    budget_statuses = []
    total_budgeted = 0.0
    total_spent = 0.0
    
    # Process each category budget
    for cat_budget in budget.category_limits:
        # Calculate spent amount for this category in this period
        spent_amount = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.user_id == current_user.id,
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
        
        budget_statuses.append(schemas.BudgetStatus(
            budget_id=cat_budget.category_id,  # Use category_id as identifier
            budget_name=cat_budget.category.name,
            budget_amount=cat_budget.budget_amount,
            spent_amount=spent_amount,
            remaining_amount=remaining,
            percentage_used=percentage_used,
            status=status
        ))
        
        total_budgeted += cat_budget.budget_amount
        total_spent += spent_amount
    
    # Overall status
    overall_percentage = (total_spent / total_budgeted * 100) if total_budgeted > 0 else 0
    if overall_percentage >= 100:
        overall_status = "over_budget"
    elif overall_percentage >= 80:
        overall_status = "near_limit"
    else:
        overall_status = "under_budget"
    
    return schemas.BudgetComparison(
        period=year_month,
        budgets=budget_statuses,
        total_budgeted=total_budgeted,
        total_spent=total_spent,
        overall_status=overall_status
    )


@router.get("/report")
def download_budget_report(
    year: int = None,
    month: int = None,
    format: str = "csv",
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Default to current month if not specified
    if not year or not month:
        today = date.today()
        year = year or today.year
        month = month or today.month
    
    # Get budget comparison data
    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == current_user.id,
        models.Budget.period == "MONTHLY"
    ).all()
    
    # Get transactions for the specified month
    transactions = db.query(models.Transaction).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.is_deleted == False,
        models.Transaction.type == "EXPENSE",
        extract('year', models.Transaction.occurred_on) == year,
        extract('month', models.Transaction.occurred_on) == month
    ).all()
    
    total_spent = sum(t.amount for t in transactions)
    
    if format.lower() == "csv":
        # Generate CSV report
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Budget Report",
            f"{year}-{month:02d}"
        ])
        writer.writerow([])  # Empty row
        writer.writerow([
            "Budget Name",
            "Budget Amount",
            "Spent Amount", 
            "Remaining",
            "Percentage Used",
            "Status"
        ])
        
        # Budget data
        total_budgeted = 0.0
        for budget in budgets:
            spent_amount = total_spent  # Simplified: assume budget covers all expenses
            remaining = budget.amount - spent_amount
            percentage_used = (spent_amount / budget.amount * 100) if budget.amount > 0 else 0
            
            if percentage_used >= 100:
                status = "Over Budget"
            elif percentage_used >= 80:
                status = "Near Limit" 
            else:
                status = "Under Budget"
            
            writer.writerow([
                budget.name,
                f"${budget.amount:.2f}",
                f"${spent_amount:.2f}",
                f"${remaining:.2f}",
                f"{percentage_used:.1f}%",
                status
            ])
            
            total_budgeted += budget.amount
        
        # Summary
        writer.writerow([])  # Empty row
        writer.writerow([
            "SUMMARY",
            f"${total_budgeted:.2f}",
            f"${total_spent:.2f}",
            f"${total_budgeted - total_spent:.2f}",
            f"{(total_spent / total_budgeted * 100) if total_budgeted > 0 else 0:.1f}%",
            ""
        ])
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=budget-report-{year}-{month:02d}.csv"
            }
        )
    
    else:
        # Return JSON format for other formats (simplified)
        budget_data = []
        total_budgeted = 0.0
        
        for budget in budgets:
            spent_amount = total_spent  # Simplified
            remaining = budget.amount - spent_amount
            percentage_used = (spent_amount / budget.amount * 100) if budget.amount > 0 else 0
            
            if percentage_used >= 100:
                status = "over_budget"
            elif percentage_used >= 80:
                status = "near_limit"
            else:
                status = "under_budget"
            
            budget_data.append({
                "budget_name": budget.name,
                "budget_amount": budget.amount,
                "spent_amount": spent_amount,
                "remaining_amount": remaining,
                "percentage_used": percentage_used,
                "status": status
            })
            
            total_budgeted += budget.amount
        
        return {
            "period": f"{year}-{month:02d}",
            "budgets": budget_data,
            "total_budgeted": total_budgeted,
            "total_spent": total_spent,
            "summary": {
                "remaining": total_budgeted - total_spent,
                "percentage_used": (total_spent / total_budgeted * 100) if total_budgeted > 0 else 0
            }
        }


@router.get("/categories")
def get_budgetable_categories(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all categories that can be used for budgeting"""
    categories = db.query(models.Category).filter(
        models.Category.user_id == current_user.id
    ).all()
    
    return categories