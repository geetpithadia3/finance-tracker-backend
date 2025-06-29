from sqlalchemy import Column, String, Float, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship
import uuid

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
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    year_month = Column(String, nullable=False)  # Format: "2024-07"
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="budgets")
    category_limits = relationship("CategoryBudget", back_populates="budget", cascade="all, delete-orphan")

class CategoryBudget(Base):
    __tablename__ = "category_budgets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    budget_id = Column(String, ForeignKey("budgets.id"))
    category_id = Column(String, ForeignKey("categories.id"))
    budget_amount = Column(Float, nullable=False)
    # REQ-004: Rollover Configuration
    rollover_unused = Column(Boolean, default=False)  # "Rollover unused funds" (Yes/No)
    rollover_overspend = Column(Boolean, default=False)  # "Deduct overspend from next month" (Yes/No)
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
    is_active = Column(Boolean, default=True)

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

class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    category_id = Column(String, ForeignKey("categories.id"))
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    next_due_date = Column(DateTime, nullable=False)
    date_flexibility = Column(String, default="EXACT")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    category = relationship("Category")

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
    
    user = relationship("User")
    category = relationship("Category") 