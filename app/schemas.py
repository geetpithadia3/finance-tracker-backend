from pydantic import BaseModel, validator, Field
from typing import List, Optional
from datetime import datetime
import re
import uuid

class CategoryBudgetCreate(BaseModel):
    category_id: str
    budget_amount: float
    
    @validator('category_id')
    def validate_category_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Invalid category ID format')
        return v
    
    @validator('budget_amount')
    def validate_budget_amount(cls, v):
        if v < 0 or v > 1000000:
            raise ValueError('Budget amount must be between 0 and 1,000,000')
        return round(v, 2)
    # REQ-004: Rollover Configuration
    rollover_enabled: Optional[bool] = False

class CategoryBudgetResponse(BaseModel):
    id: str
    category_id: str
    budget_amount: float
    # REQ-004: Rollover Configuration
    rollover_enabled: bool
    rollover_amount: float
    class Config:
        from_attributes = True

class BudgetCreate(BaseModel):
    year_month: str  # Format: "2024-07"
    category_limits: List[CategoryBudgetCreate]

class BudgetUpdate(BaseModel):
    category_limits: List[CategoryBudgetCreate]

class BudgetResponse(BaseModel):
    id: str
    year_month: str
    category_limits: List[CategoryBudgetResponse]
    created_at: datetime
    class Config:
        from_attributes = True

class BudgetCopyRequest(BaseModel):
    source_year_month: str
    target_year_month: str

class ProjectBudgetAllocationCreate(BaseModel):
    category_id: str
    allocated_amount: float

class ProjectBudgetAllocationResponse(BaseModel):
    id: str
    category_id: str
    allocated_amount: float
    class Config:
        from_attributes = True

class ProjectBudgetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    total_amount: float
    category_allocations: List[ProjectBudgetAllocationCreate]

class ProjectBudgetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    total_amount: Optional[float] = None
    category_allocations: Optional[List[ProjectBudgetAllocationCreate]] = None

class ProjectBudgetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    start_date: datetime
    end_date: datetime
    total_amount: float
    created_at: datetime
    category_allocations: List[ProjectBudgetAllocationResponse]
    class Config:
        from_attributes = True

class ProjectBudgetProgress(BaseModel):
    id: str
    name: str
    description: Optional[str]
    start_date: datetime
    end_date: datetime
    total_amount: float
    total_spent: float
    remaining_amount: float
    progress_percentage: float
    days_remaining: int
    category_progress: List[dict]

class User(BaseModel):
    id: str
    username: str
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class Category(BaseModel):
    id: str
    name: str
    class Config:
        from_attributes = True

class CategoryCreate(BaseModel):
    name: str

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class RecurringTransactionCreate(BaseModel):
    category_id: str
    amount: float
    description: str
    frequency: str
    start_date: datetime
    date_flexibility: Optional[str] = "EXACT"

class RecurringTransaction(BaseModel):
    id: str
    category_id: str
    amount: float
    description: str
    frequency: str
    start_date: datetime
    next_due_date: datetime
    date_flexibility: str
    is_active: bool
    category: Optional[Category] = None
    priority: Optional[str] = None
    class Config:
        from_attributes = True

class RecurringTransactionStatusUpdate(BaseModel):
    is_active: bool

class RecurringTransactionUpdate(BaseModel):
    category_id: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[datetime] = None
    date_flexibility: Optional[str] = None

class RecurrenceData(BaseModel):
    id: Optional[str] = None
    frequency: str
    start_date: datetime
    date_flexibility: Optional[str] = "EXACT"
    range_start: Optional[int] = None
    range_end: Optional[int] = None
    preference: Optional[str] = None
    is_variable_amount: Optional[bool] = False
    estimated_min_amount: Optional[float] = None
    estimated_max_amount: Optional[float] = None

class TransactionCreate(BaseModel):
    category_id: str
    type: str
    description: str
    amount: float
    occurred_on: datetime
    
    @validator('category_id')
    def validate_category_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Invalid category ID format')
        return v
    
    @validator('type')
    def validate_type(cls, v):
        allowed_types = ['income', 'expense', 'transfer']
        if v.lower() not in allowed_types:
            raise ValueError(f'Type must be one of: {allowed_types}')
        return v.lower()
    
    @validator('description')
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        if len(v) > 500:
            raise ValueError('Description too long (max 500 characters)')
        # Allow alphanumeric, spaces, and common punctuation
        if not re.match(r'^[a-zA-Z0-9\s\-_.,!?()&@#$%]+$', v):
            raise ValueError('Description contains invalid characters')
        return v.strip()
    
    @validator('amount')
    def validate_amount(cls, v):
        if v == 0:
            raise ValueError('Amount cannot be zero')
        if v < -1000000 or v > 1000000:
            raise ValueError('Amount out of reasonable range (-1M to 1M)')
        return round(v, 2)

class TransactionUpdate(BaseModel):
    id: str
    category_id: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    occurred_on: Optional[datetime] = None
    refunded: Optional[bool] = None
    personal_share: Optional[float] = None
    owed_share: Optional[float] = None
    share_metadata: Optional[str] = None
    recurrence: Optional[RecurrenceData] = None

class Transaction(BaseModel):
    id: str
    category_id: str
    type: str
    description: str
    amount: float
    occurred_on: datetime
    is_deleted: bool
    refunded: Optional[bool] = False
    personal_share: Optional[float] = None
    owed_share: Optional[float] = None
    share_metadata: Optional[str] = None
    created_at: Optional[datetime] = None
    category: Optional[Category] = None
    recurrence: Optional[RecurrenceData] = None
    class Config:
        from_attributes = True

class ExpenseResponse(BaseModel):
    id: str
    category_id: str
    type: str
    description: str
    amount: float
    occurred_on: datetime
    class Config:
        from_attributes = True

class ListTransactionsByMonthRequest(BaseModel):
    year: int
    month: int

class ListExpensesByMonthRequest(BaseModel):
    year: int
    month: int

class UpcomingExpense(BaseModel):
    id: str
    description: str
    amount: float
    due_date: datetime
    category: str
    is_recurring: bool = True
    variability_factor: Optional[float] = 0.0
    is_variable_amount: Optional[bool] = False
    estimated_min_amount: Optional[float] = None
    estimated_max_amount: Optional[float] = None

class PaycheckAllocation(BaseModel):
    id: str
    amount: float
    date: datetime
    source: str
    frequency: str
    expenses: List[UpcomingExpense]
    total_allocation_amount: float
    remaining_amount: float
    next_paycheck_date: Optional[datetime] = None

class AllocationResponse(BaseModel):
    paychecks: List[PaycheckAllocation] = []
    income: float = 0.0
    total_expenses: float = 0.0
    savings: float = 0.0
    month: str
    details: dict = {}

class GoalCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_amount: float
    deadline: Optional[datetime] = None
    create_temporary_category: Optional[bool] = False
    temporary_category_name: Optional[str] = None

class GoalUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[float] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = None
    linked_category_id: Optional[str] = None

class GoalResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    target_amount: float
    current_amount: float
    deadline: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    status: str
    linked_category_id: Optional[str]
    class Config:
        from_attributes = True

 