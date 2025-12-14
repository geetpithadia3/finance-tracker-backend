from pydantic import BaseModel, field_validator, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
import re
import uuid
from enum import Enum

# ============================================================================
# Authentication Schemas
# ============================================================================

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    id: str
    username: str
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Category Schemas (Expense Accounts)
# ============================================================================

class CategoryCreate(BaseModel):
    name: str

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

class Category(BaseModel):
    id: str
    name: str
    user_id: Optional[str] = None
    household_id: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Account Schemas (Assets & Liabilities)
# ============================================================================

class AccountCreate(BaseModel):
    name: str
    type: str

    @field_validator('type')
    def validate_type(cls, v):
        allowed = ['ASSET', 'LIABILITY', 'INCOME', 'EXPENSE']
        if v.upper() not in allowed:
            raise ValueError(f"Type must be one of {allowed}")
        return v.upper()

class AccountResponse(BaseModel):
    id: str
    name: str
    type: str
    balance: Optional[float] = 0.0
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Transaction Schemas (Double-Entry)
# ============================================================================

class ShareMethod(str, Enum):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"
    EQUAL = "EQUAL"

class ShareConfig(BaseModel):
    method: ShareMethod
    value: float  # amount, percent (0-100), or count (for EQUAL)

class SplitRequest(BaseModel):
    category_id: str
    amount: float
    description: str

class TransactionCreate(BaseModel):
    category_id: str
    type: str
    description: str
    amount: float
    occurred_on: datetime
    source_account_id: Optional[str] = None
    destination_account_id: Optional[str] = None
    splits: Optional[List['SplitRequest']] = None
    share: Optional[ShareConfig] = None

    @field_validator('category_id')
    def validate_category_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Invalid category ID format')
        return v

    @field_validator('source_account_id')
    def validate_source_account_id(cls, v):
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError('Invalid source account ID format')
        return v

    @field_validator('type')
    def validate_type(cls, v):
        allowed_types = ['CREDIT', 'DEBIT', 'TRANSFER']
        if v.upper() not in allowed_types:
            raise ValueError(f'Type must be one of: {allowed_types}')
        return v.upper()

    @field_validator('description')
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        if len(v) > 500:
            raise ValueError('Description too long (max 500 characters)')
        if not re.match(r'^[a-zA-Z0-9\s\-_.,!?()&@#$%]+', v):
            raise ValueError('Description contains invalid characters')
        return v.strip()

    @field_validator('amount')
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

    @field_validator('category_id')
    def validate_category_id(cls, v):
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError('Invalid category ID format')
        return v

    @field_validator('type')
    def validate_type(cls, v):
        if v is not None:
            allowed_types = ['CREDIT', 'DEBIT']
            if v.upper() not in allowed_types:
                raise ValueError(f'Type must be one of: {allowed_types}')
            return v.upper()
        return v

    @field_validator('description')
    def validate_description(cls, v):
        if v is not None:
            if not v or not v.strip():
                raise ValueError('Description cannot be empty')
            if len(v) > 500:
                raise ValueError('Description too long (max 500 characters)')
            if not re.match(r'^[a-zA-Z0-9\\s\\-_.,!?()&@#$%]+', v):
                raise ValueError('Description contains invalid characters')
            return v.strip()
        return v

    @field_validator('amount')
    def validate_amount(cls, v):
        if v is not None:
            if v == 0:
                raise ValueError('Amount cannot be zero')
            if v < -1000000 or v > 1000000:
                raise ValueError('Amount out of reasonable range (-1M to 1M)')
            return round(v, 2)
        return v

class Transaction(BaseModel):
    id: str
    user_id: str
    category_id: str
    type: str
    description: str
    amount: float
    occurred_on: datetime
    created_at: Optional[datetime] = None
    category: Optional[Category] = None
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Mapping Rule Schemas (Auto-Categorization)
# ============================================================================

class MappingRuleCreate(BaseModel):
    match_pattern: str
    target_category_id: str
    priority: int = 0

class MappingRuleResponse(BaseModel):
    id: str
    owner_id: str
    match_pattern: str
    target_category_id: str
    priority: int
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Report Schemas
# ============================================================================

class TransactionFilter(BaseModel):
    year: Optional[int] = None
    month: Optional[int] = None
    category_id: Optional[str] = None
