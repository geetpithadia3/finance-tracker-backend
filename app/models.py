from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer, ForeignKey, func, UniqueConstraint, Index
from sqlalchemy.orm import relationship
import uuid
from enum import Enum

from .database import Base
from sqlalchemy.types import JSON

class Party(Base):
    __tablename__ = "parties"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False) # 'USER', 'HOUSEHOLD'
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    party_id = Column(String, ForeignKey("parties.id"), nullable=True) # Link to Economic Actor
    
    party = relationship("Party")



# --- V2 Models (Double Entry) ---

class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("parties.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False) # 'ASSET', 'LIABILITY', 'INCOME', 'EXPENSE'
    parent_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    currency = Column(String, default='USD')
    
    owner = relationship("Party")
    parent = relationship("Account", remote_side=[id])

    __table_args__ = (
        Index('ix_accounts_owner_type', 'owner_id', 'type'),
    )

class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("parties.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    description = Column(String, nullable=False)
    notes = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    
    owner = relationship("Party")
    entries = relationship("Entry", back_populates="transaction", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_ledger_owner_date', 'owner_id', 'date'),
    )

class Entry(Base):
    __tablename__ = "entries"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String, ForeignKey("ledger_transactions.id"), nullable=False)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Float, nullable=False) # Positive = Debit, Negative = Credit
    is_reportable = Column(Boolean, default=True)
    
    transaction = relationship("LedgerTransaction", back_populates="entries")
    account = relationship("Account")

    __table_args__ = (
        Index('ix_entries_account', 'account_id'),
    )

class BudgetRule(Base):
    __tablename__ = "budget_rules"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    period = Column(String, nullable=False) # 'WEEKLY', 'MONTHLY', 'YEARLY'
    amount_limit = Column(Float, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    
    account = relationship("Account")

class RecurringTemplate(Base):
    __tablename__ = "recurring_templates"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("parties.id"), nullable=False)
    name = Column(String)
    cron_expression = Column(String)
    template_data = Column(JSON, nullable=False)
    next_run_date = Column(DateTime)
    last_run_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    owner = relationship("Party")

class MappingRule(Base):
    __tablename__ = "mapping_rules"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("parties.id"), nullable=False)
    match_pattern = Column(String, nullable=False) # Case-insensitive partial match on description
    target_category_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    priority = Column(Integer, default=0)
    
    owner = relationship("Party")
    target_category = relationship("Account") 