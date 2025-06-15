from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from typing import Union


class UserBase(BaseModel):
    username: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class User(UserBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class Category(CategoryBase):
    id: str
    user_id: str
    isEditable: bool = Field(alias="is_editable")
    isActive: bool = Field(alias="is_active")
    created_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True


class TransactionBase(BaseModel):
    type: str
    description: str
    amount: float
    occurred_on: datetime
    personal_share: Optional[float] = 0.0
    owed_share: Optional[float] = 0.0
    share_metadata: Optional[str] = None


class TransactionCreate(TransactionBase):
    category_id: str


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


class TransactionUpdate(BaseModel):
    id: str
    description: Optional[str] = None
    amount: Optional[float] = None
    occurred_on: Optional[datetime] = None
    category_id: Optional[str] = None
    is_deleted: Optional[bool] = None
    refunded: Optional[bool] = None
    personal_share: Optional[float] = None
    owed_share: Optional[float] = None
    share_metadata: Optional[str] = None
    recurrence: Optional[RecurrenceData] = None


class Transaction(TransactionBase):
    id: str
    user_id: str
    category_id: str
    is_deleted: bool
    refunded: bool
    created_at: datetime
    category: Optional[Category] = None
    recurrence: Optional[RecurrenceData] = None
    
    class Config:
        from_attributes = True


class CategoryBudgetCreate(BaseModel):
    category_id: str
    budget_amount: float


class CategoryBudgetResponse(BaseModel):
    category_id: str
    category_name: str
    budget_amount: float
    
    class Config:
        from_attributes = True


class CategoryBudgetDetailsResponse(BaseModel):
    category_id: str
    category_name: str
    budget_amount: float
    spent: float
    
    class Config:
        from_attributes = True


class BudgetCreate(BaseModel):
    year_month: str  # Format: "2024-03"
    category_limits: List[CategoryBudgetCreate]


class BudgetResponse(BaseModel):
    id: str
    year_month: str
    category_limits: List[CategoryBudgetResponse]
    
    class Config:
        from_attributes = True


class BudgetDetailsResponse(BaseModel):
    id: str
    year_month: str
    categories: List[CategoryBudgetDetailsResponse]
    
    class Config:
        from_attributes = True


# Legacy budget schema for backwards compatibility
class Budget(BaseModel):
    id: str
    user_id: str
    year_month: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class DashboardResponse(BaseModel):
    total_income: float
    total_expenses: float
    balance: float
    transactions_count: int
    expenses_by_category: dict


class BudgetStatus(BaseModel):
    budget_id: str
    budget_name: str
    budget_amount: float
    spent_amount: float
    remaining_amount: float
    percentage_used: float
    status: str  # "under_budget", "near_limit", "over_budget"


class BudgetComparison(BaseModel):
    period: str
    budgets: List[BudgetStatus]
    total_budgeted: float
    total_spent: float
    overall_status: str


class RecurringTransactionBase(BaseModel):
    description: str
    amount: float
    type: str
    frequency: str  # Will be converted to enum
    start_date: datetime
    end_date: Optional[datetime] = None
    date_flexibility: Optional[str] = "EXACT"
    priority: Optional[str] = "MEDIUM"
    is_variable_amount: Optional[bool] = False
    estimated_min_amount: Optional[float] = None
    estimated_max_amount: Optional[float] = None


class RecurringTransactionCreate(RecurringTransactionBase):
    category_id: str


class RecurringTransactionUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    frequency: Optional[str] = None
    end_date: Optional[datetime] = None
    date_flexibility: Optional[str] = None
    priority: Optional[str] = None
    is_active: Optional[bool] = None
    is_variable_amount: Optional[bool] = None
    estimated_min_amount: Optional[float] = None
    estimated_max_amount: Optional[float] = None


class RecurringTransactionStatusUpdate(BaseModel):
    is_active: bool


class RecurringTransaction(RecurringTransactionBase):
    id: str
    user_id: str
    category_id: str
    next_due_date: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category: Optional[Category] = None
    
    class Config:
        from_attributes = True


class ExpenseResponse(BaseModel):
    id: str
    description: str
    amount: float
    occurred_on: datetime
    category: Optional[Category] = None
    personal_share: float
    owed_share: float
    refunded: bool
    
    class Config:
        from_attributes = True


class ListExpensesByMonthRequest(BaseModel):
    year: int
    month: int


class ListTransactionsByMonthRequest(BaseModel):
    year: int
    month: int


# Allocation System Schemas
class UpcomingExpense(BaseModel):
    id: str
    description: str
    amount: float
    due_date: datetime
    category: str
    is_recurring: bool
    variability_factor: float = 0.0
    is_variable_amount: bool = False
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
    paychecks: List[PaycheckAllocation]