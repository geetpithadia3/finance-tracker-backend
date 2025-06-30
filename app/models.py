from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
import uuid
from enum import Enum

from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    budgets = relationship("Budget", back_populates="user")
    project_budgets = relationship("ProjectBudget", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User")
    category_budgets = relationship("CategoryBudget", back_populates="category")

class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint('user_id', 'year_month', name='uix_user_year_month'),)
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    year_month = Column(String, nullable=False)  # Format: "2024-07"
    created_at = Column(DateTime, default=func.now())
    
    # Rollover tracking fields
    rollover_last_calculated = Column(DateTime, nullable=True)
    rollover_needs_recalc = Column(Boolean, default=False)

    user = relationship("User", back_populates="budgets")
    category_limits = relationship("CategoryBudget", back_populates="budget", cascade="all, delete-orphan")

class CategoryBudget(Base):
    __tablename__ = "category_budgets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    budget_id = Column(String, ForeignKey("budgets.id"))
    category_id = Column(String, ForeignKey("categories.id"))
    budget_amount = Column(Float, nullable=False)
    # REQ-004: Rollover Configuration
    rollover_enabled = Column(Boolean, default=False)  # "Enable rollover (unused and overspend)"
    rollover_amount = Column(Float, default=0.0)  # Calculated rollover amount from previous month
    
    budget = relationship("Budget", back_populates="category_limits")
    category = relationship("Category", back_populates="category_budgets")

class ProjectBudget(Base):
    __tablename__ = "project_budgets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    description = Column(String)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    total_amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="project_budgets")
    category_allocations = relationship("ProjectBudgetAllocation", back_populates="project_budget", cascade="all, delete-orphan")

class ProjectBudgetAllocation(Base):
    __tablename__ = "project_budget_allocations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_budget_id = Column(String, ForeignKey("project_budgets.id"))
    category_id = Column(String, ForeignKey("categories.id"))
    allocated_amount = Column(Float, nullable=False)
    
    project_budget = relationship("ProjectBudget", back_populates="category_allocations")
    category = relationship("Category")

class RolloverCalculation(Base):
    __tablename__ = "rollover_calculations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    budget_id = Column(String, ForeignKey("budgets.id"), nullable=False)
    category_id = Column(String, ForeignKey("categories.id"), nullable=False)
    calculated_at = Column(DateTime, default=func.now())
    rollover_amount = Column(Float, nullable=False)
    source_month = Column(String, nullable=False)  # Format: "2024-01"
    calculation_reason = Column(String)
    base_budget = Column(Float)
    prev_rollover = Column(Float)
    effective_budget = Column(Float)
    spent_amount = Column(Float)
    created_at = Column(DateTime, default=func.now())
    
    budget = relationship("Budget")
    category = relationship("Category")

class RolloverConfig(Base):
    __tablename__ = "rollover_configs"
    __table_args__ = (UniqueConstraint('user_id', 'category_id', name='uix_user_category_rollover'),)
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    category_id = Column(String, ForeignKey("categories.id"), nullable=False)
    rollover_enabled = Column(Boolean, default=False)
    rollover_percentage = Column(Float, default=100.0)
    max_rollover_amount = Column(Float, nullable=True)
    rollover_expiry_months = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User")
    category = relationship("Category")

class RolloverChangeLog(Base):
    __tablename__ = "rollover_change_log"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    budget_id = Column(String, ForeignKey("budgets.id"), nullable=False)
    category_id = Column(String, ForeignKey("categories.id"), nullable=False)
    change_type = Column(String, nullable=False)  # recalculation, manual_override, transaction_update, budget_update
    old_rollover_amount = Column(Float, nullable=True)
    new_rollover_amount = Column(Float, nullable=True)
    trigger_reason = Column(String, nullable=True)
    changed_by = Column(String, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime, default=func.now())
    
    budget = relationship("Budget")
    category = relationship("Category")
    user = relationship("User")

class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    category_id = Column(String, ForeignKey("categories.id"))
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    type = Column(String, nullable=False)  # DEBIT, CREDIT, EXPENSE, etc.
    frequency = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    next_due_date = Column(DateTime, nullable=False)
    date_flexibility = Column(String, default="EXACT")
    range_start = Column(Integer, nullable=True)
    range_end = Column(Integer, nullable=True)
    preference = Column(String, nullable=True)
    is_variable_amount = Column(Boolean, default=False)
    estimated_min_amount = Column(Float, nullable=True)
    estimated_max_amount = Column(Float, nullable=True)
    priority = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    source_transaction_id = Column(String, ForeignKey("transactions.id"), nullable=True)
    
    category = relationship("Category")
    source_transaction = relationship(
        "Transaction",
        foreign_keys="[RecurringTransaction.source_transaction_id]"
    )

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    category_id = Column(String, ForeignKey("categories.id"))
    type = Column(String, nullable=False)  # DEBIT, CREDIT, EXPENSE, etc.
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    occurred_on = Column(DateTime, nullable=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    personal_share = Column(Float, nullable=True)
    owed_share = Column(Float, nullable=True)
    share_metadata = Column(String, nullable=True)
    refunded = Column(Boolean, default=False)
    recurring_transaction_id = Column(String, ForeignKey("recurring_transactions.id"), nullable=True)
    
    user = relationship("User")
    category = relationship("Category")
    recurring_transaction = relationship(
        "RecurringTransaction",
        backref="transactions",
        foreign_keys="[Transaction.recurring_transaction_id]"
    )

class RecurrenceFrequency(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    FOUR_WEEKLY = "FOUR_WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"

class DateFlexibility(str, Enum):
    EXACT = "EXACT"
    CUSTOM_RANGE = "CUSTOM_RANGE"
    MONTH_RANGE = "MONTH_RANGE"
    SEASONAL = "SEASONAL"

class TransactionPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH" 