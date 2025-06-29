from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CategoryBudgetCreate(BaseModel):
    category_id: str
    budget_amount: float
    # REQ-004: Rollover Configuration
    rollover_unused: Optional[bool] = False
    rollover_overspend: Optional[bool] = False

class CategoryBudgetResponse(BaseModel):
    id: str
    category_id: str
    budget_amount: float
    # REQ-004: Rollover Configuration
    rollover_unused: bool
    rollover_overspend: bool
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
    is_active: bool
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
    is_active: bool

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

class TransactionCreate(BaseModel):
    category_id: str
    type: str
    description: str
    amount: float
    occurred_on: datetime

class TransactionUpdate(BaseModel):
    id: str
    category_id: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    occurred_on: Optional[datetime] = None

class Transaction(BaseModel):
    id: str
    category_id: str
    type: str
    description: str
    amount: float
    occurred_on: datetime
    is_deleted: bool
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

class AllocationResponse(BaseModel):
    income: float = 0.0
    total_expenses: float = 0.0
    savings: float = 0.0
    month: str
    details: dict = {}

 