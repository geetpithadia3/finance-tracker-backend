from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, extract
from typing import List, Optional
from datetime import datetime, date
import calendar
import logging
import traceback

from ..database import get_db
from ..models import Budget, CategoryBudget, Transaction, Category, User, ProjectBudget, ProjectBudgetAllocation
from ..schemas import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetCopyRequest,
    CategoryBudgetResponse, ProjectBudgetCreate, ProjectBudgetUpdate, 
    ProjectBudgetResponse, ProjectBudgetProgress
)
from ..auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/budgets", tags=["budgets"])

@router.get("/projects/test")
def test_projects_route():
    """Test endpoint to verify /budgets/projects routing works"""
    logger.info("TEST: /budgets/projects/test endpoint accessed successfully")
    return {"message": "Projects route is working", "status": "success", "timestamp": datetime.now().isoformat()}

def check_budget_overlap(db: Session, user_id: str, category_id: str, start_date: datetime, end_date: datetime, exclude_budget_id: str = None):
    """
    Check if a category has overlapping budget periods for the given date range.
    Returns list of conflicting budgets if any overlap is found.
    """
    conflicts = []
    
    # Check monthly budgets for overlap
    monthly_budgets = db.query(Budget).filter(
        and_(
            Budget.user_id == user_id,
            Budget.is_active == True,
            Budget.id != exclude_budget_id if exclude_budget_id else True
        )
    ).all()
    
    for budget in monthly_budgets:
        # Check if this budget has the category
        category_budget = db.query(CategoryBudget).filter(
            and_(
                CategoryBudget.budget_id == budget.id,
                CategoryBudget.category_id == category_id
            )
        ).first()
        
        if category_budget:
            # Calculate monthly budget date range
            year, month = map(int, budget.year_month.split('-'))
            budget_start = datetime(year, month, 1)
            # Get last day of the month
            last_day = calendar.monthrange(year, month)[1]
            budget_end = datetime(year, month, last_day, 23, 59, 59)
            
            # Check for overlap
            if not (end_date < budget_start or start_date > budget_end):
                conflicts.append({
                    'type': 'monthly',
                    'budget_id': budget.id,
                    'budget_name': f"Monthly Budget for {budget.year_month}",
                    'period': f"{budget.year_month}",
                    'allocated_amount': category_budget.budget_amount
                })
    
    # Check project budgets for overlap  
    project_budgets = db.query(ProjectBudget).filter(
        and_(
            ProjectBudget.user_id == user_id,
            ProjectBudget.is_active == True,
            ProjectBudget.id != exclude_budget_id if exclude_budget_id else True
        )
    ).all()
    
    for project_budget in project_budgets:
        # Check if this project budget has the category
        allocation = db.query(ProjectBudgetAllocation).filter(
            and_(
                ProjectBudgetAllocation.project_budget_id == project_budget.id,
                ProjectBudgetAllocation.category_id == category_id
            )
        ).first()
        
        if allocation:
            # Check for overlap with project dates
            if not (end_date < project_budget.start_date or start_date > project_budget.end_date):
                conflicts.append({
                    'type': 'project',
                    'budget_id': project_budget.id,
                    'budget_name': project_budget.name,
                    'period': f"{project_budget.start_date.strftime('%Y-%m-%d')} to {project_budget.end_date.strftime('%Y-%m-%d')}",
                    'allocated_amount': allocation.allocated_amount
                })
    
    return conflicts

def calculate_rollover_amounts(db: Session, user_id: str, current_year_month: str, category_id: str):
    """
    REQ-004: Calculate rollover amounts from previous month's budget
    Returns: (rollover_amount, source_budget_info)
    """
    # Parse current month to get previous month
    year, month = map(int, current_year_month.split('-'))
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year = year - 1
    
    prev_year_month = f"{prev_year}-{prev_month:02d}"
    
    # Get previous month's budget for this category
    prev_budget = db.query(Budget).filter(
        and_(
            Budget.user_id == user_id,
            Budget.year_month == prev_year_month,
            Budget.is_active == True
        )
    ).first()
    
    if not prev_budget:
        return 0.0, None
    
    # Get previous month's category budget
    prev_category_budget = db.query(CategoryBudget).filter(
        and_(
            CategoryBudget.budget_id == prev_budget.id,
            CategoryBudget.category_id == category_id
        )
    ).first()
    
    if not prev_category_budget:
        return 0.0, None
    
    # Calculate actual spending for previous month
    prev_year_obj, prev_month_obj = prev_year, prev_month
    spent_amount = db.query(Transaction).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.is_deleted == False,
            extract('year', Transaction.occurred_on) == prev_year_obj,
            extract('month', Transaction.occurred_on) == prev_month_obj,
            Transaction.type.in_(['DEBIT', 'EXPENSE'])
        )
    ).all()
    
    total_spent = sum(abs(t.amount) for t in spent_amount)
    unused_amount = prev_category_budget.budget_amount - total_spent
    
    rollover_amount = 0.0
    
    # Apply rollover rules
    if unused_amount > 0 and prev_category_budget.rollover_unused:
        # Rollover unused funds
        rollover_amount = unused_amount
    elif unused_amount < 0 and prev_category_budget.rollover_overspend:
        # Deduct overspend (negative rollover)
        rollover_amount = unused_amount
    
    return rollover_amount, {
        'prev_year_month': prev_year_month,
        'budget_amount': prev_category_budget.budget_amount,
        'spent_amount': total_spent,
        'unused_amount': unused_amount,
        'rollover_unused': prev_category_budget.rollover_unused,
        'rollover_overspend': prev_category_budget.rollover_overspend
    }

@router.post("/", response_model=BudgetResponse)
def create_budget(
    budget: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new monthly budget for any month/year with category-based spending limits"""
    
    logger.info(f"Creating budget for user {current_user.id} for period {budget.year_month}")
    logger.debug(f"Budget data: {budget.dict()}")
    
    try:
        # Validate input data
        if not budget.year_month:
            logger.error("Missing year_month in budget data")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="year_month is required and cannot be empty"
            )
        
        if not budget.category_limits or len(budget.category_limits) == 0:
            logger.error("No category limits provided in budget data")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one category limit is required"
            )
        
        # Validate year_month format
        try:
            year, month = map(int, budget.year_month.split('-'))
            if year < 2000 or year > 3000 or month < 1 or month > 12:
                raise ValueError("Invalid date range")
        except (ValueError, AttributeError) as e:
            logger.error(f"Invalid year_month format: {budget.year_month}, error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid year_month format '{budget.year_month}'. Expected format: YYYY-MM (e.g., 2024-01)"
            )
        
        # Check if budget already exists for this month
        logger.debug(f"Checking for existing budget for {budget.year_month}")
        existing_budget = db.query(Budget).filter(
            and_(
                Budget.user_id == current_user.id,
                Budget.year_month == budget.year_month,
                Budget.is_active == True
            )
        ).first()
        
        if existing_budget:
            logger.warning(f"Budget already exists for user {current_user.id} in {budget.year_month}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "duplicate_budget",
                    "message": f"Budget already exists for {budget.year_month}",
                    "existing_budget_id": existing_budget.id,
                    "year_month": budget.year_month
                }
            )
        
        # Validate categories exist and belong to user
        logger.debug(f"Validating {len(budget.category_limits)} category limits")
        category_ids = [limit.category_id for limit in budget.category_limits]
        
        # Check for duplicate categories
        if len(category_ids) != len(set(category_ids)):
            duplicate_ids = [cid for cid in set(category_ids) if category_ids.count(cid) > 1]
            logger.error(f"Duplicate categories found: {duplicate_ids}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "duplicate_categories",
                    "message": "Duplicate categories are not allowed in the same budget",
                    "duplicate_category_ids": duplicate_ids
                }
            )
        
        # Validate budget amounts
        for i, limit in enumerate(budget.category_limits):
            if not limit.category_id:
                logger.error(f"Empty category_id at index {i}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category ID is required for limit at index {i}"
                )
            
            if limit.budget_amount is None or limit.budget_amount < 0:
                logger.error(f"Invalid budget amount {limit.budget_amount} for category {limit.category_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "invalid_budget_amount",
                        "message": f"Budget amount must be a positive number",
                        "category_id": limit.category_id,
                        "provided_amount": limit.budget_amount
                    }
                )
        
        # Check if categories exist and belong to user
        categories = db.query(Category).filter(
            and_(
                Category.id.in_(category_ids),
                Category.user_id == current_user.id,
                Category.is_active == True
            )
        ).all()
        
        found_category_ids = {cat.id for cat in categories}
        missing_category_ids = [cid for cid in category_ids if cid not in found_category_ids]
        
        if missing_category_ids:
            logger.error(f"Categories not found or not owned by user: {missing_category_ids}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_categories",
                    "message": "One or more categories not found or not owned by user",
                    "missing_category_ids": missing_category_ids,
                    "user_id": current_user.id
                }
            )
        
        # REQ-003: Check for budget overlap conflicts
        year, month = map(int, budget.year_month.split('-'))
        month_start = datetime(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        month_end = datetime(year, month, last_day, 23, 59, 59)
        
        overlapping_categories = []
        for limit in budget.category_limits:
            conflicts = check_budget_overlap(
                db, current_user.id, limit.category_id, 
                month_start, month_end
            )
            if conflicts:
                category_name = next((c.name for c in categories if c.id == limit.category_id), 'Unknown')
                overlapping_categories.append({
                    'category_id': limit.category_id,
                    'category_name': category_name,
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
        logger.info(f"Creating budget record for {budget.year_month}")
        db_budget = Budget(
            user_id=current_user.id,
            year_month=budget.year_month,
            is_active=True
        )
        db.add(db_budget)
        db.flush()
        logger.debug(f"Created budget with ID: {db_budget.id}")
        
        # Create category limits
        logger.debug(f"Creating {len(budget.category_limits)} category limits")
        for i, limit in enumerate(budget.category_limits):
            # REQ-004: Calculate rollover amount from previous month
            try:
                rollover_amount, rollover_info = calculate_rollover_amounts(
                    db, current_user.id, budget.year_month, limit.category_id
                )
                logger.debug(f"Rollover calculated for category {limit.category_id}: {rollover_amount}")
            except Exception as e:
                logger.warning(f"Could not calculate rollover for category {limit.category_id}: {e}")
                rollover_amount = 0.0
            
            category_budget = CategoryBudget(
                budget_id=db_budget.id,
                category_id=limit.category_id,
                budget_amount=limit.budget_amount,
                # REQ-004: Rollover Configuration
                rollover_unused=getattr(limit, 'rollover_unused', False),
                rollover_overspend=getattr(limit, 'rollover_overspend', False),
                rollover_amount=rollover_amount
            )
            db.add(category_budget)
            logger.debug(f"Added category limit {i+1}/{len(budget.category_limits)}: {limit.category_id} = ${limit.budget_amount}")
    
        db.commit()
        db.refresh(db_budget)
        
        logger.info(f"Successfully created budget {db_budget.id} for user {current_user.id} in {budget.year_month}")
        return db_budget
        
    except HTTPException as e:
        # Log HTTP exceptions but re-raise them as-is (these are validation errors)
        logger.warning(f"Validation error creating budget for user {current_user.id}: {e.detail}")
        db.rollback()
        raise
    except Exception as e:
        # Log unexpected errors with full traceback
        error_msg = f"Unexpected error creating budget for user {current_user.id} in {budget.year_month if budget else 'unknown'}"
        logger.error(f"{error_msg}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Rollback the transaction
        try:
            db.rollback()
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {rollback_error}")
        
        # Return detailed error information
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while creating the budget",
                "error_type": type(e).__name__,
                "error_details": str(e),
                "user_id": current_user.id,
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/", response_model=List[BudgetResponse])
def list_budgets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all user budgets"""
    budgets = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.is_active == True
        )
    ).order_by(Budget.year_month.desc()).offset(skip).limit(limit).all()
    
    return budgets

# Project Budget Endpoints - Must come before /{year_month} route to avoid conflicts

@router.get("/projects-simple")
def simple_test():
    """Simple test endpoint without dependencies"""
    return {"message": "Project budgets route is working", "status": "success"}

@router.get("/projects-test")
def test_project_budgets_table(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test endpoint to check if project budget tables exist"""
    try:
        # Try to query the table
        count = db.query(ProjectBudget).count()
        return {
            "status": "success", 
            "message": f"Project budgets table exists with {count} records",
            "user_id": current_user.id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Project budgets table issue: {str(e)}",
            "user_id": current_user.id
        }

@router.post("/projects", response_model=ProjectBudgetResponse)
def create_project_budget(
    project_budget: ProjectBudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create multi-month project budget with category allocations"""
    logger.info(f"Creating project budget '{project_budget.name}' for user {current_user.id}")
    logger.debug(f"Project budget data: {project_budget.dict()}")
    
    try:
        # Input validation
        if not project_budget.name or not project_budget.name.strip():
            logger.error("Project budget name is required")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project budget name is required and cannot be empty"
            )
        
        if project_budget.total_amount <= 0:
            logger.error(f"Invalid total amount: {project_budget.total_amount}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_total_amount",
                    "message": "Total amount must be greater than zero",
                    "provided_amount": project_budget.total_amount
                }
            )
        
        # Validate that end_date is after start_date
        if project_budget.end_date <= project_budget.start_date:
            logger.error(f"Invalid date range: {project_budget.start_date} to {project_budget.end_date}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_date_range",
                    "message": "End date must be after start date",
                    "start_date": project_budget.start_date.isoformat(),
                    "end_date": project_budget.end_date.isoformat()
                }
            )
        
        # Validate categories exist and belong to user
        category_ids = [allocation.category_id for allocation in project_budget.category_allocations]
        categories = db.query(Category).filter(
            and_(
                Category.id.in_(category_ids),
                Category.user_id == current_user.id,
                Category.is_active == True
            )
        ).all()
        
        if len(categories) != len(category_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more categories not found or not owned by user"
            )
        
        # Validate that total allocations don't exceed total budget
        total_allocated = sum(allocation.allocated_amount for allocation in project_budget.category_allocations)
        if total_allocated > project_budget.total_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total allocations ({total_allocated}) exceed total budget ({project_budget.total_amount})"
            )
        
        # REQ-003: Check for budget overlap conflicts
        overlapping_categories = []
        for allocation in project_budget.category_allocations:
            conflicts = check_budget_overlap(
                db, current_user.id, allocation.category_id,
                project_budget.start_date, project_budget.end_date
            )
            if conflicts:
                category_name = next((c.name for c in categories if c.id == allocation.category_id), 'Unknown')
                overlapping_categories.append({
                    'category_id': allocation.category_id,
                    'category_name': category_name,
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
        logger.info(f"Creating project budget record for '{project_budget.name}'")
        db_project_budget = ProjectBudget(
            user_id=current_user.id,
            name=project_budget.name,
            description=project_budget.description,
            start_date=project_budget.start_date,
            end_date=project_budget.end_date,
            total_amount=project_budget.total_amount,
            is_active=True
        )
        db.add(db_project_budget)
        db.flush()
        logger.debug(f"Created project budget with ID: {db_project_budget.id}")
        
        # Create category allocations
        logger.debug(f"Creating {len(project_budget.category_allocations)} category allocations")
        for i, allocation in enumerate(project_budget.category_allocations):
            db_allocation = ProjectBudgetAllocation(
                project_budget_id=db_project_budget.id,
                category_id=allocation.category_id,
                allocated_amount=allocation.allocated_amount
            )
            db.add(db_allocation)
            logger.debug(f"Added allocation {i+1}/{len(project_budget.category_allocations)}: {allocation.category_id} = ${allocation.allocated_amount}")
        
        db.commit()
        db.refresh(db_project_budget)
        
        logger.info(f"Successfully created project budget '{project_budget.name}' with ID: {db_project_budget.id} for user {current_user.id}")
        return db_project_budget
        
    except HTTPException as e:
        # Log HTTP exceptions but re-raise them as-is (these are validation errors)
        logger.warning(f"Validation error creating project budget '{project_budget.name}' for user {current_user.id}: {e.detail}")
        db.rollback()
        raise
    except Exception as e:
        # Log unexpected errors with full traceback
        error_msg = f"Unexpected error creating project budget '{project_budget.name}' for user {current_user.id}"
        logger.error(f"{error_msg}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Rollback the transaction
        try:
            db.rollback()
        except Exception as rollback_error:
            logger.error(f"Error during rollback: {rollback_error}")
        
        # Return detailed error information
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "An unexpected error occurred while creating the project budget",
                "error_type": type(e).__name__,
                "error_details": str(e),
                "project_name": project_budget.name,
                "user_id": current_user.id,
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/projects", response_model=List[ProjectBudgetResponse])
def list_project_budgets(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all project budgets"""
    logger.info(f"GET /budgets/projects - User: {current_user.id}, skip={skip}, limit={limit}, active_only={active_only}")
    
    try:
        # Log authentication info
        logger.debug(f"Authenticated user: {current_user.username} (ID: {current_user.id})")
        
        # Check if ProjectBudget table exists and is accessible
        try:
            total_count = db.query(ProjectBudget).count()
            logger.debug(f"Total project budgets in database: {total_count}")
        except Exception as table_error:
            logger.error(f"Error accessing ProjectBudget table: {table_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "database_table_error",
                    "message": "Cannot access project_budgets table",
                    "details": str(table_error)
                }
            )
        
        # Build query with logging
        logger.debug("Building query for project budgets")
        query = db.query(ProjectBudget).filter(ProjectBudget.user_id == current_user.id)
        
        if active_only:
            logger.debug("Adding active_only filter")
            query = query.filter(ProjectBudget.is_active == True)
        
        # Log the SQL query (for debugging)
        try:
            sql_query = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
            logger.debug(f"SQL Query: {sql_query}")
        except Exception:
            logger.debug("Could not compile SQL query for logging")
        
        # Execute query
        logger.debug(f"Executing query with offset={skip}, limit={limit}")
        project_budgets = query.order_by(ProjectBudget.start_date.desc()).offset(skip).limit(limit).all()
        
        logger.info(f"Found {len(project_budgets)} project budgets for user {current_user.id}")
        
        # Log details of found budgets
        if project_budgets:
            for i, pb in enumerate(project_budgets):
                logger.debug(f"Project {i+1}: ID={pb.id}, Name='{pb.name}', Active={pb.is_active}, "
                           f"Start={pb.start_date}, End={pb.end_date}")
        else:
            logger.debug("No project budgets found for this user")
        
        # Log response data
        logger.debug(f"Returning {len(project_budgets)} project budgets")
        return project_budgets
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in list_project_budgets: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "internal_server_error",
                "message": "Error fetching project budgets",
                "error_type": type(e).__name__,
                "error_details": str(e),
                "user_id": current_user.id
            }
        )

@router.get("/projects/{project_budget_id}", response_model=ProjectBudgetResponse)
def get_project_budget(
    project_budget_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get specific project budget"""
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
    
    return project_budget

@router.put("/projects/{project_budget_id}", response_model=ProjectBudgetResponse)
def update_project_budget(
    project_budget_id: str,
    project_budget_update: ProjectBudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update project budget"""
    # Get existing project budget
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
    
    # Validate categories exist and belong to user
    category_ids = [allocation.category_id for allocation in project_budget_update.category_allocations]
    categories = db.query(Category).filter(
        and_(
            Category.id.in_(category_ids),
            Category.user_id == current_user.id,
            Category.is_active == True
        )
    ).all()
    
    if len(categories) != len(category_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more categories not found or not owned by user"
        )
    
    # Validate that total allocations don't exceed total budget
    total_allocated = sum(allocation.allocated_amount for allocation in project_budget_update.category_allocations)
    if total_allocated > project_budget_update.total_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Total allocations ({total_allocated}) exceed total budget ({project_budget_update.total_amount})"
        )
    
    # REQ-003: Check for budget overlap conflicts (exclude current budget)
    overlapping_categories = []
    for allocation in project_budget_update.category_allocations:
        conflicts = check_budget_overlap(
            db, current_user.id, allocation.category_id,
            project_budget_update.start_date, project_budget_update.end_date,
            exclude_budget_id=project_budget_id
        )
        if conflicts:
            category_name = next((c.name for c in categories if c.id == allocation.category_id), 'Unknown')
            overlapping_categories.append({
                'category_id': allocation.category_id,
                'category_name': category_name,
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
    
    # Update project budget fields
    project_budget.name = project_budget_update.name
    project_budget.description = project_budget_update.description
    project_budget.start_date = project_budget_update.start_date
    project_budget.end_date = project_budget_update.end_date
    project_budget.total_amount = project_budget_update.total_amount
    
    # Delete existing allocations and create new ones
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
    
    # Soft delete by setting is_active to False
    project_budget.is_active = False
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
    
    # Calculate spending for each category within the project date range
    category_progress = []
    total_spent = 0.0
    
    allocations = db.query(ProjectBudgetAllocation).filter(
        ProjectBudgetAllocation.project_budget_id == project_budget_id
    ).all()
    
    for allocation in allocations:
        # Get category name
        category = db.query(Category).filter(Category.id == allocation.category_id).first()
        category_name = category.name if category else 'Unknown Category'
        
        # Get transactions for this category within the project date range
        spent = db.query(Transaction).filter(
            and_(
                Transaction.user_id == current_user.id,
                Transaction.category_id == allocation.category_id,
                Transaction.occurred_on >= project_budget.start_date,
                Transaction.occurred_on <= project_budget.end_date,
                Transaction.amount < 0  # Only expenses
            )
        ).with_entities(Transaction.amount).all()
        
        category_spent = abs(sum(row[0] for row in spent)) if spent else 0.0
        total_spent += category_spent
        
        category_progress.append({
            'category_id': allocation.category_id,
            'category_name': category_name,
            'allocated_amount': allocation.allocated_amount,
            'spent_amount': category_spent,
            'remaining': allocation.allocated_amount - category_spent,
            'percentage_used': (category_spent / allocation.allocated_amount * 100) if allocation.allocated_amount > 0 else 0
        })
    
    # Calculate days remaining
    from datetime import datetime
    current_date = datetime.now()
    days_remaining = max(0, (project_budget.end_date - current_date).days)
    
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
        'category_progress': category_progress,
        'is_active': project_budget.is_active
    }

@router.get("/{year_month}", response_model=BudgetResponse)
def get_budget_by_month(
    year_month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get budget by specific year-month"""
    budget = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.year_month == year_month,
            Budget.is_active == True
        )
    ).first()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget not found for {year_month}"
        )
    
    return budget

@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: str,
    budget_update: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update existing monthly budget allocations"""
    
    # Get existing budget
    budget = db.query(Budget).filter(
        and_(
            Budget.id == budget_id,
            Budget.user_id == current_user.id,
            Budget.is_active == True
        )
    ).first()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    
    # Validate categories exist and belong to user
    category_ids = [limit.category_id for limit in budget_update.category_limits]
    categories = db.query(Category).filter(
        and_(
            Category.id.in_(category_ids),
            Category.user_id == current_user.id,
            Category.is_active == True
        )
    ).all()
    
    if len(categories) != len(category_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more categories not found or not owned by user"
        )
    
    # REQ-003: Check for budget overlap conflicts (exclude current budget)
    year, month = map(int, budget.year_month.split('-'))
    month_start = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    month_end = datetime(year, month, last_day, 23, 59, 59)
    
    overlapping_categories = []
    for limit in budget_update.category_limits:
        conflicts = check_budget_overlap(
            db, current_user.id, limit.category_id, 
            month_start, month_end, exclude_budget_id=budget_id
        )
        if conflicts:
            category_name = next((c.name for c in categories if c.id == limit.category_id), 'Unknown')
            overlapping_categories.append({
                'category_id': limit.category_id,
                'category_name': category_name,
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
        category_budget = CategoryBudget(
            budget_id=budget_id,
            category_id=limit.category_id,
            budget_amount=limit.budget_amount,
            # REQ-004: Rollover Configuration
            rollover_unused=getattr(limit, 'rollover_unused', False),
            rollover_overspend=getattr(limit, 'rollover_overspend', False),
            rollover_amount=0.0  # Will be calculated during rollover
        )
        db.add(category_budget)
    
    db.commit()
    db.refresh(budget)
    
    return budget

@router.delete("/{budget_id}")
def delete_budget(
    budget_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete monthly budget"""
    
    budget = db.query(Budget).filter(
        and_(
            Budget.id == budget_id,
            Budget.user_id == current_user.id,
            Budget.is_active == True
        )
    ).first()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found"
        )
    
    # Soft delete
    budget.is_active = False
    db.commit()
    
    return {"detail": "Budget deleted successfully"}

@router.post("/copy", response_model=BudgetResponse)
def copy_budget(
    copy_request: BudgetCopyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Copy budget from previous month"""
    
    # Check if target budget already exists
    target_budget = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.year_month == copy_request.target_year_month,
            Budget.is_active == True
        )
    ).first()
    
    if target_budget:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Budget already exists for {copy_request.target_year_month}"
        )
    
    # Get source budget
    source_budget = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.year_month == copy_request.source_year_month,
            Budget.is_active == True
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
        year_month=copy_request.target_year_month,
        is_active=True
    )
    db.add(new_budget)
    db.flush()
    
    # Copy category limits
    for category_limit in source_budget.category_limits:
        new_category_limit = CategoryBudget(
            budget_id=new_budget.id,
            category_id=category_limit.category_id,
            budget_amount=category_limit.budget_amount
        )
        db.add(new_category_limit)
    
    db.commit()
    db.refresh(new_budget)
    
    return new_budget

@router.get("/{year_month}/spending", response_model=dict)
def get_budget_spending(
    year_month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current spending against budget limits for a specific month"""
    
    # Get budget
    budget = db.query(Budget).filter(
        and_(
            Budget.user_id == current_user.id,
            Budget.year_month == year_month,
            Budget.is_active == True
        )
    ).first()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Budget not found for {year_month}"
        )
    
    # Parse year and month
    try:
        year, month = map(int, year_month.split('-'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid year_month format. Use YYYY-MM"
        )
    
    # Calculate spending per category for the month
    spending_data = {}
    total_budgeted = 0
    total_spent = 0
    
    for category_limit in budget.category_limits:
        # Get actual spending for this category in this month
        spent = db.query(Transaction).filter(
            and_(
                Transaction.user_id == current_user.id,
                Transaction.category_id == category_limit.category_id,
                Transaction.is_deleted == False,
                extract('year', Transaction.occurred_on) == year,
                extract('month', Transaction.occurred_on) == month,
                Transaction.type.in_(['DEBIT', 'EXPENSE'])  # Only count expenses
            )
        ).all()
        
        spent_amount = sum(abs(t.amount) for t in spent)
        budget_amount = category_limit.budget_amount
        # REQ-004: Include rollover amount in effective budget
        effective_budget = budget_amount + category_limit.rollover_amount
        remaining = effective_budget - spent_amount
        
        # Get category name
        category = db.query(Category).filter(Category.id == category_limit.category_id).first()
        
        spending_data[category_limit.category_id] = {
            'category_name': category.name if category else 'Unknown',
            'budget_amount': budget_amount,
            'spent_amount': spent_amount,
            'remaining_amount': remaining,
            'percentage_used': (spent_amount / effective_budget * 100) if effective_budget > 0 else 0,
            'status': 'over' if spent_amount > effective_budget else 'warning' if spent_amount > effective_budget * 0.75 else 'good',
            # REQ-004: Rollover information
            'rollover_amount': category_limit.rollover_amount,
            'effective_budget': effective_budget,
            'rollover_unused': category_limit.rollover_unused,
            'rollover_overspend': category_limit.rollover_overspend
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
