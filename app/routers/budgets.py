from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import calendar
import logging
import asyncio

from ..database import get_db
from ..models import Budget, CategoryBudget, Transaction, Category, User, ProjectBudget, ProjectBudgetAllocation, RolloverCalculation
from ..schemas import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetCopyRequest,
    ProjectBudgetCreate, ProjectBudgetUpdate, ProjectBudgetResponse, ProjectBudgetProgress
)
from ..auth import get_current_user
from app.websockets import broadcast_rollover_update

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/budgets", tags=["budgets"])

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_spending_for_category(db: Session, user_id: str, category_id: str, 
                            start_date: datetime, end_date: datetime) -> float:
    """Get total spending for a category in the given date range"""
    # Ensure dates are timezone-aware for comparison
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    
    transactions = db.query(Transaction).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.occurred_on >= start_date,
            Transaction.occurred_on <= end_date,
            Transaction.amount < 0,  # Only expenses
            Transaction.is_deleted == False
        )
    ).all()
    
    return abs(sum(t.amount for t in transactions))

def calculate_month_dates(year_month: str) -> tuple[datetime, datetime]:
    """Calculate start and end dates for a month"""
    year, month = map(int, year_month.split('-'))
    start_date = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start_date, end_date

def get_category_names(db: Session, category_ids: List[str]) -> Dict[str, str]:
    """Get category names for given IDs"""
    categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
    return {cat.id: cat.name for cat in categories}

def calculate_rollover_amount(db: Session, user_id: str, category_id: str, current_month: str, 
                            record_history: bool = True) -> float:
    """Calculate rollover amount from previous month"""
    try:
        year, month = map(int, current_month.split('-'))
        
        # Get previous month
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        
        prev_year_month = f"{prev_year}-{prev_month:02d}"
        
        # Get previous month's budget
        prev_budget = db.query(Budget).filter(
            and_(Budget.user_id == user_id, Budget.year_month == prev_year_month)
        ).first()
        
        if not prev_budget:
            return 0.0
        
        # Get category budget for previous month
        prev_category_budget = db.query(CategoryBudget).filter(
            and_(
                CategoryBudget.budget_id == prev_budget.id,
                CategoryBudget.category_id == category_id
            )
        ).first()
        
        if not prev_category_budget:
            return 0.0
        
        # Calculate spending for previous month
        start_date, end_date = calculate_month_dates(prev_year_month)
        spent_amount = get_spending_for_category(db, user_id, category_id, start_date, end_date)
        
        # Calculate rollover based on configuration
        # CRITICAL FIX: Use effective budget (base + previous rollover) instead of just base budget
        prev_effective_budget = prev_category_budget.budget_amount + (prev_category_budget.rollover_amount or 0.0)
        difference = prev_effective_budget - spent_amount
        
        # Log rollover calculation for debugging
        logger.info(f"Rollover calculation for category {category_id} from {prev_year_month} to {current_month}: "
                   f"base_budget=${prev_category_budget.budget_amount}, "
                   f"prev_rollover=${prev_category_budget.rollover_amount or 0.0}, "
                   f"effective_budget=${prev_effective_budget}, "
                   f"spent=${spent_amount}, difference=${difference}")
        
        rollover_amount = 0.0
        if difference > 0 and prev_category_budget.rollover_enabled:
            logger.info(f"Applying positive rollover: ${difference}")
            rollover_amount = difference  # Positive rollover (unused funds)
        elif difference < 0 and prev_category_budget.rollover_enabled:
            logger.info(f"Applying negative rollover: ${difference}")
            rollover_amount = difference  # Negative rollover (overspend)
        else:
            logger.info(f"No rollover applied (enabled={prev_category_budget.rollover_enabled})")
        
        # Note: History recording will be done by the calling function after budget creation
        
        return rollover_amount, prev_category_budget.budget_amount, prev_category_budget.rollover_amount or 0.0, prev_effective_budget, spent_amount
    except Exception as e:
        logger.warning(f"Could not calculate rollover for category {category_id}: {e}")
        return 0.0, 0.0, 0.0, 0.0, 0.0

def record_rollover_calculation(db: Session, budget_id: str, category_id: str, 
                              rollover_amount: float, source_month: str, 
                              calculation_reason: str, base_budget: Optional[float] = None,
                              prev_rollover: Optional[float] = None, effective_budget: Optional[float] = None,
                              spent_amount: Optional[float] = None):
    """Record rollover calculation in history table"""
    try:
        
        calculation = RolloverCalculation(
            budget_id=budget_id,
            category_id=category_id,
            rollover_amount=rollover_amount,
            source_month=source_month,
            calculation_reason=calculation_reason,
            base_budget=base_budget,
            prev_rollover=prev_rollover,
            effective_budget=effective_budget,
            spent_amount=spent_amount
        )
        
        db.add(calculation)
        # Note: Don't commit here, let the calling function handle the transaction
        logger.info(f"Recorded rollover calculation: {rollover_amount} for category {category_id} from {source_month}")
        
    except Exception as e:
        logger.warning(f"Failed to record rollover calculation: {e}")

def mark_rollover_for_recalculation(db: Session, budget_id: str, reason: str = "data_change"):
    """Mark a budget as needing rollover recalculation"""
    try:
        
        budget = db.query(Budget).filter(Budget.id == budget_id).first()
        if budget:
            budget.rollover_needs_recalc = True
            logger.info(f"Marked budget {budget_id} for rollover recalculation: {reason}")
            
    except Exception as e:
        logger.warning(f"Failed to mark budget for recalculation: {e}")

def invalidate_rollover_chain(db: Session, user_id: str, changed_month: str, reason: str = "transaction_change"):
    """Invalidate rollover calculations for all months after the changed month"""
    try:
        
        # Get all budgets after the changed month for this user
        budgets = db.query(Budget).filter(
            and_(
                Budget.user_id == user_id,
                Budget.year_month > changed_month
            )
        ).all()
        
        for budget in budgets:
            budget.rollover_needs_recalc = True
            logger.info(f"Invalidated rollover for budget {budget.year_month} due to {reason} in {changed_month}")
            
    except Exception as e:
        logger.warning(f"Failed to invalidate rollover chain: {e}")

@router.get("/{year_month}/rollover-status")
def get_rollover_status(
    year_month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get rollover calculation status for a budget"""
    budget = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.year_month == year_month
        )
    ).first()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget not found for {year_month}"
        )
    
    return {
        "year_month": year_month,
        "rollover_last_calculated": budget.rollover_last_calculated,
        "rollover_needs_recalc": budget.rollover_needs_recalc,
        "calculation_pending": budget.rollover_needs_recalc and budget.rollover_last_calculated is None
    }

def _perform_rollover_recalculation(db: Session, user_id: str, year_month: str, reason: str = "system_recalculation"):
    """Internal function to perform rollover recalculation for a specific month."""
    budget = db.query(Budget).filter(
        and_(
            Budget.user_id == user_id,
            Budget.year_month == year_month
        )
    ).first()

    if not budget:
        logger.info(f"No budget found for {year_month} for user {user_id}. Skipping recalculation.")
        return {"message": f"Budget not found for {year_month}", "updated_categories": 0}

    updated_categories = 0
    try:
        for category_budget in budget.category_limits:
            old_rollover = category_budget.rollover_amount or 0.0
            new_rollover, base_budget, prev_rollover, effective_budget, spent_amount = calculate_rollover_amount(
                db, user_id, category_budget.category_id, year_month, record_history=False
            )

            if abs(new_rollover - old_rollover) > 0.01:  # Only update if significant change
                category_budget.rollover_amount = new_rollover
                updated_categories += 1

                # Record the recalculation in history
                try:
                    # Get previous month for history record
                    year_int, month_int = map(int, year_month.split('-'))
                    if month_int == 1:
                        prev_year, prev_month = year_int - 1, 12
                    else:
                        prev_year, prev_month = year_int, month_int - 1
                    prev_year_month = f"{prev_year}-{prev_month:02d}"

                    record_rollover_calculation(
                        db, budget.id, category_budget.category_id, 
                        new_rollover, prev_year_month,
                        reason, base_budget, prev_rollover, effective_budget, spent_amount
                    )
                except Exception as e:
                    logger.warning(f"Failed to record rollover recalculation history for {year_month}, category {category_budget.category_id}: {e}")

        # Mark as recalculated
        budget.rollover_last_calculated = func.now()
        budget.rollover_needs_recalc = False

        db.commit() # Commit changes for this budget

        logger.info(f"Recalculated rollover for {year_month}: {updated_categories} categories updated")

        return {
            "message": f"Rollover recalculated for {year_month}",
            "updated_categories": updated_categories,
            "recalculated_at": budget.rollover_last_calculated
        }

    except Exception as e:
        db.rollback() # Rollback if any error occurs during this budget's recalculation
        logger.error(f"Failed to recalculate rollover for {year_month}: {e}")
        raise

@router.post("/{year_month}/recalculate-rollover")
def recalculate_rollover_endpoint(
    year_month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """API endpoint to force recalculation of rollover for a specific month."""
    try:
        result = _perform_rollover_recalculation(db, current_user.id, year_month, "manual_recalculation")
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recalculate rollover: {str(e)}"
        )

def invalidate_rollover_chain(db: Session, user_id: str, changed_month: str, reason: str = "transaction_change"):
    """Invalidate and trigger recalculation for rollover calculations for all months after the changed month."""
    try:
        # Get all budgets after the changed month for this user, ordered chronologically
        budgets_to_recalc = db.query(Budget).filter(
            and_(
                Budget.user_id == user_id,
                Budget.year_month > changed_month
            )
        ).order_by(Budget.year_month).all()

        for budget in budgets_to_recalc:
            logger.info(f"Invalidating and recalculating rollover for budget {budget.year_month} due to {reason} in {changed_month}")
            # Mark as needing recalculation (even if we recalculate immediately, this flag is useful)
            budget.rollover_needs_recalc = True
            db.flush() # Flush to ensure the flag is set before recalculation

            # Perform recalculation for this month
            try:
                _perform_rollover_recalculation(db, user_id, budget.year_month, reason)
            except Exception as e:
                logger.error(f"Error during chained rollover recalculation for {budget.year_month}: {e}")
                # Continue to next month even if one fails, but log the error
                db.rollback() # Rollback any partial changes for this budget
                # Re-fetch the budget to ensure it's not in a detached state if rollback occurred
                budget = db.query(Budget).filter(Budget.id == budget.id).first()
                if budget:
                    budget.rollover_needs_recalc = True # Mark again if recalculation failed
                    db.flush()

        db.commit() # Final commit for all invalidations and recalculations
        logger.info(f"Rollover chain invalidation and recalculation completed for months after {changed_month}.")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to invalidate and recalculate rollover chain: {e}")

def check_budget_conflicts(db: Session, user_id: str, category_id: str, 
                         start_date: datetime, end_date: datetime, 
                         exclude_budget_id: str = None) -> List[Dict]:
    """Check for budget overlap conflicts"""
    conflicts = []
    
    # Check monthly budgets
    monthly_budgets = db.query(Budget).filter(
        and_(
            Budget.user_id == user_id,
            Budget.id != exclude_budget_id if exclude_budget_id else True
        )
    ).all()
    
    for budget in monthly_budgets:
        category_budget = db.query(CategoryBudget).filter(
            and_(
                CategoryBudget.budget_id == budget.id,
                CategoryBudget.category_id == category_id
            )
        ).first()
        
        if category_budget:
            month_start, month_end = calculate_month_dates(budget.year_month)
            if not (end_date < month_start or start_date > month_end):
                conflicts.append({
                    'type': 'monthly',
                    'budget_id': budget.id,
                    'budget_name': f"Monthly Budget for {budget.year_month}",
                    'period': budget.year_month,
                    'allocated_amount': category_budget.budget_amount
                })
    
    # Check project budgets
    project_budgets = db.query(ProjectBudget).filter(
        and_(
            ProjectBudget.user_id == user_id,
            ProjectBudget.id != exclude_budget_id if exclude_budget_id else True
        )
    ).all()
    
    for project in project_budgets:
        allocation = db.query(ProjectBudgetAllocation).filter(
            and_(
                ProjectBudgetAllocation.project_budget_id == project.id,
                ProjectBudgetAllocation.category_id == category_id
            )
        ).first()
        
        if allocation:
            # Ensure all dates are timezone-aware for comparison
            project_start = project.start_date
            project_end = project.end_date
            
            if project_start.tzinfo is None:
                project_start = project_start.replace(tzinfo=timezone.utc)
            if project_end.tzinfo is None:
                project_end = project_end.replace(tzinfo=timezone.utc)
            
            if not (end_date < project_start or start_date > project_end):
                conflicts.append({
                    'type': 'project',
                    'budget_id': project.id,
                    'budget_name': project.name,
                    'period': f"{project_start.strftime('%Y-%m-%d')} to {project_end.strftime('%Y-%m-%d')}",
                    'allocated_amount': allocation.allocated_amount
                })
    
    return conflicts

def validate_categories_owned_by_user(db: Session, user_id: str, category_ids: List[str]) -> bool:
    """Validate that all categories belong to the user"""
    categories = db.query(Category).filter(
        and_(
            Category.id.in_(category_ids),
            Category.user_id == user_id,
            Category.is_active == True
        )
    ).all()
    return len(categories) == len(category_ids)

# ============================================================================
# MONTHLY BUDGET ENDPOINTS
# ============================================================================

@router.post("/", response_model=BudgetResponse)
def create_monthly_budget(
    budget: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new monthly budget"""
    try:
        # Validate categories
        category_ids = [limit.category_id for limit in budget.category_limits]
        if not validate_categories_owned_by_user(db, current_user.id, category_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more categories not found or not owned by user"
            )
        
        # Check for conflicts
        start_date, end_date = calculate_month_dates(budget.year_month)
        category_names = get_category_names(db, category_ids)
        
        overlapping_categories = []
        for limit in budget.category_limits:
            conflicts = check_budget_conflicts(
                db, current_user.id, limit.category_id, start_date, end_date
            )
            if conflicts:
                overlapping_categories.append({
                    'category_id': limit.category_id,
                    'category_name': category_names.get(limit.category_id, 'Unknown'),
                    'conflicts': conflicts
                })
        
        if overlapping_categories:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Category already budgeted for this period",
                    "overlapping_categories": overlapping_categories
                }
            )
        
        # Create budget
        db_budget = Budget(
            user_id=current_user.id,
            year_month=budget.year_month
        )
        db.add(db_budget)
        db.flush()
        
        # Create category limits with rollover
        for limit in budget.category_limits:
            rollover_amount, base_budget, prev_rollover, effective_budget, spent_amount = calculate_rollover_amount(
                db, current_user.id, limit.category_id, budget.year_month
            )
            
            category_budget = CategoryBudget(
                budget_id=db_budget.id,
                category_id=limit.category_id,
                budget_amount=limit.budget_amount,
                rollover_enabled=getattr(limit, 'rollover_enabled', False),
                rollover_amount=rollover_amount
            )
            db.add(category_budget)
        
        db.commit()
        db.refresh(db_budget)
        
        # Record rollover calculation history after successful budget creation
        try:
            for category_budget in db_budget.category_limits:
                if category_budget.rollover_amount and category_budget.rollover_amount != 0.0:
                    # Get previous month for history record
                    year, month = map(int, budget.year_month.split('-'))
                    if month == 1:
                        prev_year, prev_month = year - 1, 12
                    else:
                        prev_year, prev_month = year, month - 1
                    prev_year_month = f"{prev_year}-{prev_month:02d}"
                    
                    record_rollover_calculation(
                        db, db_budget.id, category_budget.category_id, 
                        category_budget.rollover_amount, prev_year_month,
                        "budget_creation", base_budget, prev_rollover, effective_budget, spent_amount
                    )
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to record rollover history during budget creation: {e}")
        
        return db_budget
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create budget"
        )

# ============================================================================
# PROJECT BUDGET ENDPOINTS (Must come before /{year_month} route)
# ============================================================================

@router.get("/projects", response_model=List[ProjectBudgetResponse])
def list_project_budgets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all project budgets"""
    query = db.query(ProjectBudget).filter(ProjectBudget.user_id == current_user.id)
    
    project_budgets = query.order_by(ProjectBudget.start_date.desc()).offset(skip).limit(limit).all()
    return project_budgets

@router.post("/projects", response_model=ProjectBudgetResponse)
def create_project_budget(
    project_budget: ProjectBudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project budget"""
    try:
        # Validate input
        if not project_budget.name or not project_budget.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project budget name is required"
            )
        
        if project_budget.total_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Total amount must be greater than zero"
            )
        
        if project_budget.end_date <= project_budget.start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        # Validate categories
        category_ids = [allocation.category_id for allocation in project_budget.category_allocations]
        if not validate_categories_owned_by_user(db, current_user.id, category_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more categories not found or not owned by user"
            )
        
        # Validate allocations don't exceed total
        total_allocated = sum(allocation.allocated_amount for allocation in project_budget.category_allocations)
        if total_allocated > project_budget.total_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total allocations ({total_allocated}) exceed total budget ({project_budget.total_amount})"
            )
        
        # Check for conflicts
        category_names = get_category_names(db, category_ids)
        overlapping_categories = []
        
        for allocation in project_budget.category_allocations:
            conflicts = check_budget_conflicts(
                db, current_user.id, allocation.category_id,
                project_budget.start_date, project_budget.end_date
            )
            if conflicts:
                overlapping_categories.append({
                    'category_id': allocation.category_id,
                    'category_name': category_names.get(allocation.category_id, 'Unknown'),
                    'conflicts': conflicts
                })
        
        if overlapping_categories:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Category already budgeted for this period",
                    "overlapping_categories": overlapping_categories
                }
            )
        
        # Create project budget
        # Ensure dates are timezone-aware
        start_date = project_budget.start_date
        end_date = project_budget.end_date
        
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        
        db_project_budget = ProjectBudget(
            user_id=current_user.id,
            name=project_budget.name,
            description=project_budget.description,
            start_date=start_date,
            end_date=end_date,
            total_amount=project_budget.total_amount
        )
        db.add(db_project_budget)
        db.flush()
        
        # Create allocations
        for allocation in project_budget.category_allocations:
            db_allocation = ProjectBudgetAllocation(
                project_budget_id=db_project_budget.id,
                category_id=allocation.category_id,
                allocated_amount=allocation.allocated_amount
            )
            db.add(db_allocation)
        
        db.commit()
        db.refresh(db_project_budget)
        return db_project_budget
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating project budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project budget"
        )

@router.put("/projects/{project_budget_id}", response_model=ProjectBudgetResponse)
def update_project_budget(
    project_budget_id: str,
    project_budget_update: ProjectBudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update project budget"""
    project_budget = db.query(ProjectBudget).filter(
        and_(
            ProjectBudget.id == project_budget_id,
            ProjectBudget.user_id == current_user.id
        )
    ).first()
    
    if not project_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project budget not found"
        )
    
    try:
        # Validate categories if provided
        if project_budget_update.category_allocations:
            category_ids = [allocation.category_id for allocation in project_budget_update.category_allocations]
            if not validate_categories_owned_by_user(db, current_user.id, category_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="One or more categories not found or not owned by user"
                )
            
            # Validate allocations don't exceed total
            total_amount = project_budget_update.total_amount or project_budget.total_amount
            total_allocated = sum(allocation.allocated_amount for allocation in project_budget_update.category_allocations)
            if total_allocated > total_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Total allocations ({total_allocated}) exceed total budget ({total_amount})"
                )
        
        # Update fields
        if project_budget_update.name:
            project_budget.name = project_budget_update.name
        if project_budget_update.description is not None:
            project_budget.description = project_budget_update.description
        if project_budget_update.start_date:
            start_date = project_budget_update.start_date
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            project_budget.start_date = start_date
        if project_budget_update.end_date:
            end_date = project_budget_update.end_date
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            project_budget.end_date = end_date
        if project_budget_update.total_amount:
            project_budget.total_amount = project_budget_update.total_amount
        
        # Update allocations if provided
        if project_budget_update.category_allocations:
            # Delete existing allocations
            db.query(ProjectBudgetAllocation).filter(
                ProjectBudgetAllocation.project_budget_id == project_budget_id
            ).delete()
            
            # Create new allocations
            for allocation in project_budget_update.category_allocations:
                db_allocation = ProjectBudgetAllocation(
                    project_budget_id=project_budget.id,
                    category_id=allocation.category_id,
                    allocated_amount=allocation.allocated_amount
                )
                db.add(db_allocation)
        
        db.commit()
        db.refresh(project_budget)
        return project_budget
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating project budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project budget"
        )

@router.delete("/projects/{project_budget_id}")
def delete_project_budget(
    project_budget_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) project budget"""
    project_budget = db.query(ProjectBudget).filter(
        and_(
            ProjectBudget.id == project_budget_id,
            ProjectBudget.user_id == current_user.id
        )
    ).first()
    
    if not project_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project budget not found"
        )
    
    db.delete(project_budget)
    db.commit()
    return {"message": "Project budget deleted successfully"}

@router.get("/projects/{project_budget_id}/progress", response_model=ProjectBudgetProgress)
def get_project_budget_progress(
    project_budget_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get project budget spending progress"""
    project_budget = db.query(ProjectBudget).filter(
        and_(
            ProjectBudget.id == project_budget_id,
            ProjectBudget.user_id == current_user.id
        )
    ).first()
    
    if not project_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project budget not found"
        )
    
    # Get allocations and calculate progress
    allocations = db.query(ProjectBudgetAllocation).filter(
        ProjectBudgetAllocation.project_budget_id == project_budget_id
    ).all()
    
    category_names = get_category_names(db, [a.category_id for a in allocations])
    category_progress = []
    total_spent = 0.0
    
    for allocation in allocations:
        spent_amount = get_spending_for_category(
            db, current_user.id, allocation.category_id,
            project_budget.start_date, project_budget.end_date
        )
        
        total_spent += spent_amount
        
        category_progress.append({
            'category_id': allocation.category_id,
            'category_name': category_names.get(allocation.category_id, 'Unknown Category'),
            'allocated_amount': allocation.allocated_amount,
            'spent_amount': spent_amount,
            'remaining': allocation.allocated_amount - spent_amount,
            'percentage_used': (spent_amount / allocation.allocated_amount * 100) if allocation.allocated_amount > 0 else 0
        })
    
    # Calculate days remaining
    current_date = datetime.now(timezone.utc)
    
    # Ensure both dates are timezone-aware for comparison
    end_date = project_budget.end_date
    if end_date.tzinfo is None:
        # If end_date is timezone-naive, assume it's UTC
        end_date = end_date.replace(tzinfo=timezone.utc)
    
    days_remaining = max(0, (end_date - current_date).days)
    
    return {
        'id': project_budget.id,
        'name': project_budget.name,
        'description': project_budget.description,
        'start_date': project_budget.start_date,
        'end_date': project_budget.end_date,
        'total_amount': project_budget.total_amount,
        'total_spent': total_spent,
        'remaining_amount': project_budget.total_amount - total_spent,
        'progress_percentage': (total_spent / project_budget.total_amount * 100) if project_budget.total_amount > 0 else 0,
        'days_remaining': days_remaining,
        'category_progress': category_progress
    }

# ============================================================================
# MONTHLY BUDGET ENDPOINTS
# ============================================================================

@router.get("/debug/all")
def debug_all_budgets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Debug: List all budgets with details"""
    budgets = db.query(Budget).filter(Budget.user_id == current_user.id).all()
    result = []
    for budget in budgets:
        result.append({
            "id": budget.id,
            "year_month": budget.year_month,
            "created_at": budget.created_at.isoformat(),
            "category_count": len(budget.category_limits)
        })
    return result

@router.get("/", response_model=List[BudgetResponse])
def list_monthly_budgets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all monthly budgets"""
    budgets = db.query(Budget).filter(
        Budget.user_id == current_user.id
    ).order_by(Budget.year_month.desc()).offset(skip).limit(limit).all()
    
    logger.info(f"Found {len(budgets)} budgets for user {current_user.id}")
    for budget in budgets:
        logger.info(f"Budget: id={budget.id}, year_month={budget.year_month}")
    
    return budgets

@router.get("/{year_month}", response_model=BudgetResponse)
def get_monthly_budget(
    year_month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get monthly budget by year-month"""
    logger.info(f"Fetching budget for user {current_user.id}, month {year_month}")
    
    budget = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.year_month == year_month
        )
    ).first()
    
    if not budget:
        logger.info(f"No budget found for {year_month}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget not found for {year_month}"
        )
    
    logger.info(f"Found budget: id={budget.id}, year_month={budget.year_month}, categories={len(budget.category_limits)}")
    return budget

@router.put("/{budget_id}", response_model=BudgetResponse)
def update_monthly_budget(
    budget_id: str,
    budget_update: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update monthly budget"""
    logger.info(f"Updating budget: id={budget_id}, user={current_user.id}")
    
    budget = db.query(Budget).filter(
        and_(
            Budget.id == budget_id,
            Budget.user_id == current_user.id
        )
    ).first()
    
    if budget:
        logger.info(f"Budget to update: id={budget.id}, year_month={budget.year_month}")
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    
    try:
        # Validate categories
        category_ids = [limit.category_id for limit in budget_update.category_limits]
        if not validate_categories_owned_by_user(db, current_user.id, category_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more categories not found or not owned by user"
            )
        
        # Check for conflicts (excluding current budget)
        start_date, end_date = calculate_month_dates(budget.year_month)
        category_names = get_category_names(db, category_ids)
        
        overlapping_categories = []
        for limit in budget_update.category_limits:
            conflicts = check_budget_conflicts(
                db, current_user.id, limit.category_id, start_date, end_date, budget_id
            )
            if conflicts:
                overlapping_categories.append({
                    'category_id': limit.category_id,
                    'category_name': category_names.get(limit.category_id, 'Unknown'),
                    'conflicts': conflicts
                })
        
        if overlapping_categories:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Category already budgeted for this period",
                    "overlapping_categories": overlapping_categories
                }
            )
        
        # Delete existing category limits
        db.query(CategoryBudget).filter(CategoryBudget.budget_id == budget_id).delete()
        
        # Create new category limits
        for limit in budget_update.category_limits:
            rollover_amount = calculate_rollover_amount(
                db, current_user.id, limit.category_id, budget.year_month
            )
            
            category_budget = CategoryBudget(
                budget_id=budget.id,
                category_id=limit.category_id,
                budget_amount=limit.budget_amount,
                rollover_enabled=getattr(limit, 'rollover_enabled', False),
                rollover_amount=rollover_amount
            )
            db.add(category_budget)
        
        db.commit()
        db.refresh(budget)
        logger.info(f"Budget updated successfully: id={budget.id}, year_month={budget.year_month}")
        # Invalidate rollover for all future months after this budget
        invalidate_rollover_chain(db, current_user.id, budget.year_month, reason="budget_update")
        db.commit()
        # Broadcast WebSocket update for each affected month (including this one and future months)
        try:
            # Find all affected months (this and future months)
            affected_budgets = db.query(Budget).filter(
                Budget.user_id == current_user.id,
                Budget.year_month >= budget.year_month
            ).all()
            for b in affected_budgets:
                asyncio.create_task(broadcast_rollover_update({"month": b.year_month}))
        except Exception as e:
            logger.warning(f"Failed to broadcast rollover update: {e}")
        return budget
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating budget: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update budget"
        )

@router.delete("/{budget_id}")
def delete_monthly_budget(
    budget_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) monthly budget"""
    budget = db.query(Budget).filter(
        and_(
            Budget.id == budget_id,
            Budget.user_id == current_user.id
        )
    ).first()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    
    db.delete(budget)
    db.commit()
    return {"message": "Budget deleted successfully"}

@router.post("/copy", response_model=BudgetResponse)
def copy_monthly_budget(
    copy_request: BudgetCopyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Copy budget from one month to another"""
    source_budget = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.year_month == copy_request.source_year_month
        )
    ).first()
    
    if not source_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source budget not found for {copy_request.source_year_month}"
        )
    
    # Create new budget
    new_budget = Budget(
        user_id=current_user.id,
        year_month=copy_request.target_year_month
    )
    db.add(new_budget)
    db.flush()
    
    # Copy category limits
    for category_limit in source_budget.category_limits:
        rollover_amount, base_budget, prev_rollover, effective_budget, spent_amount = calculate_rollover_amount(
            db, current_user.id, category_limit.category_id, copy_request.target_year_month
        )
        
        new_category_limit = CategoryBudget(
            budget_id=new_budget.id,
            category_id=category_limit.category_id,
            budget_amount=category_limit.budget_amount,
            rollover_enabled=category_limit.rollover_enabled,
            rollover_amount=rollover_amount
        )
        db.add(new_category_limit)
    
    db.commit()
    db.refresh(new_budget)
    
    # Record rollover calculation history after successful budget copy
    try:
        for category_budget in new_budget.category_limits:
            if category_budget.rollover_amount and category_budget.rollover_amount != 0.0:
                # Get previous month for history record
                year, month = map(int, copy_request.target_year_month.split('-'))
                if month == 1:
                    prev_year, prev_month = year - 1, 12
                else:
                    prev_year, prev_month = year, month - 1
                prev_year_month = f"{prev_year}-{prev_month:02d}"
                
                record_rollover_calculation(
                    db, new_budget.id, category_budget.category_id, 
                    category_budget.rollover_amount, prev_year_month,
                    "budget_copy", None, None, None, None
                )
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to record rollover history during budget copy: {e}")
    
    return new_budget

@router.get("/{year_month}/spending")
def get_monthly_spending(
    year_month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get spending data for a monthly budget"""
    budget = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.year_month == year_month
        )
    ).first()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget not found for {year_month}"
        )
    
    start_date, end_date = calculate_month_dates(year_month)
    category_names = get_category_names(db, [cl.category_id for cl in budget.category_limits])
    
    spending_data = {}
    total_budgeted = 0
    total_spent = 0
    
    for category_limit in budget.category_limits:
        spent_amount = get_spending_for_category(
            db, current_user.id, category_limit.category_id, start_date, end_date
        )
        
        effective_budget = category_limit.budget_amount + category_limit.rollover_amount
        remaining = effective_budget - spent_amount
        progress_percentage = (spent_amount / effective_budget * 100) if effective_budget > 0 else 0
        
        spending_data[category_limit.category_id] = {
            'category_id': category_limit.category_id,
            'category_name': category_names.get(category_limit.category_id, 'Unknown'),
            'budget_amount': category_limit.budget_amount,
            'rollover_amount': category_limit.rollover_amount,
            'effective_budget': effective_budget,
            'spent_amount': spent_amount,
            'remaining_amount': remaining,
            'progress_percentage': progress_percentage,
            'is_over_budget': spent_amount > effective_budget
        }
        
        total_budgeted += effective_budget
        total_spent += spent_amount
    
    return {
        'year_month': year_month,
        'total_budgeted': total_budgeted,
        'total_spent': total_spent,
        'total_remaining': total_budgeted - total_spent,
        'categories': spending_data
    }

