from sqlalchemy import Column, String, Float, DateTime, Boolean, ForeignKey, Text, Integer, Enum
from sqlalchemy.orm import relationship
from sqlalchemy import func
from app.database import Base
import uuid
import enum


# Enums matching Kotlin app
class RecurrenceFrequency(enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    BIWEEKLY = "BIWEEKLY"
    FOUR_WEEKLY = "FOUR_WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class DateFlexibility(enum.Enum):
    EXACT = "EXACT"
    EARLY_MONTH = "EARLY_MONTH"
    MID_MONTH = "MID_MONTH"
    LATE_MONTH = "LATE_MONTH"
    CUSTOM_RANGE = "CUSTOM_RANGE"
    WEEKDAY = "WEEKDAY"
    WEEKEND = "WEEKEND"
    MONTH_RANGE = "MONTH_RANGE"
    SEASON = "SEASON"


class TransactionPriority(enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user")
    categories = relationship("Category", back_populates="user")
    budgets = relationship("Budget", back_populates="user")
    recurring_transactions = relationship("RecurringTransaction", back_populates="user")


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"))
    is_editable = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    recurring_transactions = relationship("RecurringTransaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False)  # INCOME, EXPENSE
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    occurred_on = Column(DateTime, nullable=False)
    is_deleted = Column(Boolean, default=False)
    refunded = Column(Boolean, default=False)
    personal_share = Column(Float, default=0.0)
    owed_share = Column(Float, default=0.0)
    share_metadata = Column(Text)
    created_at = Column(DateTime, default=func.now())
    
    # Foreign keys
    user_id = Column(String, ForeignKey("users.id"))
    category_id = Column(String, ForeignKey("categories.id"))
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    recurring_transaction = relationship("RecurringTransaction", back_populates="source_transaction", uselist=False)


class Budget(Base):
    __tablename__ = "budgets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    year_month = Column(String, nullable=False)  # Format: "2024-03"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="budgets")
    category_limits = relationship("CategoryBudget", back_populates="budget", cascade="all, delete-orphan")


class CategoryBudget(Base):
    __tablename__ = "category_budgets"
    
    budget_id = Column(String, ForeignKey("budgets.id"), primary_key=True)
    category_id = Column(String, ForeignKey("categories.id"), primary_key=True)
    budget_amount = Column(Float, nullable=False)
    
    # Relationships
    budget = relationship("Budget", back_populates="category_limits")
    category = relationship("Category")


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # INCOME, EXPENSE
    
    # Enhanced frequency and flexibility options
    frequency = Column(Enum(RecurrenceFrequency), nullable=False, default=RecurrenceFrequency.MONTHLY)
    date_flexibility = Column(Enum(DateFlexibility), nullable=False, default=DateFlexibility.EXACT)
    priority = Column(Enum(TransactionPriority), nullable=False, default=TransactionPriority.MEDIUM)
    
    # Date flexibility specific fields
    range_start = Column(Integer)  # For CUSTOM_RANGE flexibility
    range_end = Column(Integer)    # For CUSTOM_RANGE flexibility
    preference = Column(String)    # For day of week, season, etc.
    
    # Date management
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)  # Optional end date
    next_due_date = Column(DateTime, nullable=False)
    
    # Status and tracking
    is_active = Column(Boolean, default=True)
    
    # Variable amount support
    is_variable_amount = Column(Boolean, default=False)
    estimated_min_amount = Column(Float)
    estimated_max_amount = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Foreign keys
    user_id = Column(String, ForeignKey("users.id"))
    category_id = Column(String, ForeignKey("categories.id"))
    source_transaction_id = Column(String, ForeignKey("transactions.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="recurring_transactions")
    category = relationship("Category", back_populates="recurring_transactions")
    source_transaction = relationship("Transaction", back_populates="recurring_transaction")