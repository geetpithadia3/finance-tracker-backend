# Database Models and Schema Documentation

This document provides comprehensive documentation for all database models and validation schemas used in the Finance Tracker Backend application.

## Table of Contents

1. [Overview](#overview)
2. [Database Models (SQLAlchemy)](#database-models-sqlalchemy)
3. [Validation Schemas (Pydantic)](#validation-schemas-pydantic)
4. [Entity Relationships](#entity-relationships)
5. [Enumerations](#enumerations)
6. [Validation Rules](#validation-rules)

---

## Overview

The Finance Tracker Backend uses:
- **ORM**: SQLAlchemy for database operations
- **Validation**: Pydantic for request/response validation
- **Databases**: SQLite (development) and PostgreSQL (production)
- **ID Strategy**: UUID-based primary keys for all entities

### File Locations

- **Database Models**: `/app/models.py`
- **Validation Schemas**: `/app/schemas.py`
- **Database Configuration**: `/app/database.py`

---

## Database Models (SQLAlchemy)

All database models are defined in `/app/models.py` and inherit from SQLAlchemy's `Base` class.

### 1. User

**Purpose**: Stores user account information and authentication credentials.

**Table Name**: `users`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique user identifier |
| `username` | String | Unique, Not Null | - | User's login username |
| `password` | String | Not Null | - | Hashed password |
| `created_at` | DateTime | - | Current timestamp | Account creation timestamp |
| `is_active` | Boolean | - | `True` | Account active status |

**Relationships**:
- `budgets`: One-to-many with `Budget`
- `project_budgets`: One-to-many with `ProjectBudget`

**Location**: app/models.py:8-16

---

### 2. Category

**Purpose**: Defines transaction categories for organizing financial data.

**Table Name**: `categories`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique category identifier |
| `name` | String | Not Null | - | Category name |
| `user_id` | String (UUID) | Foreign Key → `users.id` | - | Owner user ID |
| `is_active` | Boolean | - | `True` | Whether category is active |
| `created_at` | DateTime | - | Current timestamp | Creation timestamp |
| `is_temporary` | Boolean | - | `False` | Indicates temporary category for goals |
| `linked_goal_id` | String (UUID) | Foreign Key → `goals.id`, Nullable | `None` | Associated goal ID |

**Relationships**:
- `user`: Many-to-one with `User`
- `category_budgets`: One-to-many with `CategoryBudget`

**Location**: app/models.py:18-29

---

### 3. Budget

**Purpose**: Represents a monthly budget for a user with rollover tracking.

**Table Name**: `budgets`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique budget identifier |
| `user_id` | String (UUID) | Foreign Key → `users.id` | - | Owner user ID |
| `year_month` | String | Not Null | - | Budget month (format: "YYYY-MM") |
| `created_at` | DateTime | - | Current timestamp | Creation timestamp |
| `rollover_last_calculated` | DateTime | Nullable | `None` | Last rollover calculation time |
| `rollover_needs_recalc` | Boolean | - | `False` | Flag for rollover recalculation |

**Unique Constraints**:
- `(user_id, year_month)`: Ensures one budget per user per month

**Relationships**:
- `user`: Many-to-one with `User`
- `category_limits`: One-to-many with `CategoryBudget` (cascade delete)

**Location**: app/models.py:31-45

---

### 4. CategoryBudget

**Purpose**: Defines budget allocation for a specific category within a monthly budget, including rollover configuration.

**Table Name**: `category_budgets`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique category budget identifier |
| `budget_id` | String (UUID) | Foreign Key → `budgets.id` | - | Parent budget ID |
| `category_id` | String (UUID) | Foreign Key → `categories.id` | - | Category ID |
| `budget_amount` | Float | Not Null | - | Allocated budget amount |
| `rollover_enabled` | Boolean | - | `False` | Whether rollover is enabled |
| `rollover_amount` | Float | - | `0.0` | Calculated rollover from previous month |

**Relationships**:
- `budget`: Many-to-one with `Budget`
- `category`: Many-to-one with `Category`

**Business Logic**: Supports REQ-004 - Rollover Configuration for unused and overspend amounts.

**Location**: app/models.py:47-58

---

### 5. ProjectBudget

**Purpose**: Time-bounded budget for specific projects with category allocations.

**Table Name**: `project_budgets`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique project budget identifier |
| `user_id` | String (UUID) | Foreign Key → `users.id` | - | Owner user ID |
| `name` | String | Not Null | - | Project name |
| `description` | String | - | - | Project description |
| `start_date` | DateTime | Not Null | - | Project start date |
| `end_date` | DateTime | Not Null | - | Project end date |
| `total_amount` | Float | Not Null | - | Total project budget |
| `created_at` | DateTime | - | Current timestamp | Creation timestamp |

**Relationships**:
- `user`: Many-to-one with `User`
- `category_allocations`: One-to-many with `ProjectBudgetAllocation` (cascade delete)

**Location**: app/models.py:60-72

---

### 6. ProjectBudgetAllocation

**Purpose**: Allocates portions of a project budget to specific categories.

**Table Name**: `project_budget_allocations`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique allocation identifier |
| `project_budget_id` | String (UUID) | Foreign Key → `project_budgets.id` | - | Parent project budget ID |
| `category_id` | String (UUID) | Foreign Key → `categories.id` | - | Category ID |
| `allocated_amount` | Float | Not Null | - | Amount allocated to category |

**Relationships**:
- `project_budget`: Many-to-one with `ProjectBudget`
- `category`: Many-to-one with `Category`

**Location**: app/models.py:74-82

---

### 7. RolloverConfig

**Purpose**: User-defined configuration for budget rollover behavior per category.

**Table Name**: `rollover_configs`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique config identifier |
| `user_id` | String (UUID) | Foreign Key → `users.id`, Not Null | - | Owner user ID |
| `category_id` | String (UUID) | Foreign Key → `categories.id`, Not Null | - | Category ID |
| `rollover_enabled` | Boolean | - | `False` | Whether rollover is enabled |
| `rollover_percentage` | Float | - | `100.0` | Percentage of unused budget to roll over |
| `max_rollover_amount` | Float | Nullable | `None` | Maximum rollover cap |
| `rollover_expiry_months` | Integer | Nullable | `None` | Number of months before rollover expires |
| `created_at` | DateTime | - | Current timestamp | Creation timestamp |
| `updated_at` | DateTime | - | Current timestamp | Last update timestamp |

**Unique Constraints**:
- `(user_id, category_id)`: One rollover config per user per category

**Relationships**:
- `user`: Many-to-one with `User`
- `category`: Many-to-one with `Category`

**Location**: app/models.py:103-118

---

### 8. RolloverCalculation

**Purpose**: Audit trail for rollover calculations with detailed breakdown.

**Table Name**: `rollover_calculations`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique calculation identifier |
| `budget_id` | String (UUID) | Foreign Key → `budgets.id`, Not Null | - | Budget ID |
| `category_id` | String (UUID) | Foreign Key → `categories.id`, Not Null | - | Category ID |
| `calculated_at` | DateTime | - | Current timestamp | Calculation timestamp |
| `rollover_amount` | Float | Not Null | - | Calculated rollover amount |
| `source_month` | String | Not Null | - | Source month (format: "YYYY-MM") |
| `calculation_reason` | String | - | - | Reason for calculation |
| `base_budget` | Float | - | - | Base budget amount |
| `prev_rollover` | Float | - | - | Previous rollover amount |
| `effective_budget` | Float | - | - | Effective budget (base + rollover) |
| `spent_amount` | Float | - | - | Amount spent |
| `created_at` | DateTime | - | Current timestamp | Record creation timestamp |

**Relationships**:
- `budget`: Many-to-one with `Budget`
- `category`: Many-to-one with `Category`

**Location**: app/models.py:84-101

---

### 9. RolloverChangeLog

**Purpose**: Tracks changes to rollover amounts for audit purposes.

**Table Name**: `rollover_change_log`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique log entry identifier |
| `budget_id` | String (UUID) | Foreign Key → `budgets.id`, Not Null | - | Budget ID |
| `category_id` | String (UUID) | Foreign Key → `categories.id`, Not Null | - | Category ID |
| `change_type` | String | Not Null | - | Type of change (recalculation, manual_override, transaction_update, budget_update) |
| `old_rollover_amount` | Float | Nullable | - | Previous rollover amount |
| `new_rollover_amount` | Float | Nullable | - | New rollover amount |
| `trigger_reason` | String | Nullable | - | Reason for change |
| `changed_by` | String (UUID) | Foreign Key → `users.id`, Nullable | - | User who made the change |
| `changed_at` | DateTime | - | Current timestamp | Change timestamp |

**Relationships**:
- `budget`: Many-to-one with `Budget`
- `category`: Many-to-one with `Category`
- `user`: Many-to-one with `User`

**Change Types**:
- `recalculation`: Automatic rollover recalculation
- `manual_override`: Manual adjustment by user
- `transaction_update`: Updated due to transaction changes
- `budget_update`: Updated due to budget changes

**Location**: app/models.py:120-135

---

### 10. Transaction

**Purpose**: Records individual financial transactions (income, expenses, transfers).

**Table Name**: `transactions`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique transaction identifier |
| `user_id` | String (UUID) | Foreign Key → `users.id` | - | Owner user ID |
| `category_id` | String (UUID) | Foreign Key → `categories.id` | - | Category ID |
| `type` | String | Not Null | - | Transaction type (DEBIT, CREDIT, EXPENSE, etc.) |
| `description` | String | Not Null | - | Transaction description |
| `amount` | Float | Not Null | - | Transaction amount |
| `occurred_on` | DateTime | Not Null | - | Transaction date |
| `is_deleted` | Boolean | - | `False` | Soft delete flag |
| `created_at` | DateTime | - | Current timestamp | Creation timestamp |
| `personal_share` | Float | Nullable | - | User's personal share (for shared expenses) |
| `owed_share` | Float | Nullable | - | Amount owed by others |
| `share_metadata` | String | Nullable | - | Additional sharing information |
| `refunded` | Boolean | - | `False` | Whether transaction was refunded |
| `recurring_transaction_id` | String (UUID) | Foreign Key → `recurring_transactions.id`, Nullable | - | Associated recurring transaction |

**Relationships**:
- `user`: Many-to-one with `User`
- `category`: Many-to-one with `Category`
- `recurring_transaction`: Many-to-one with `RecurringTransaction`

**Business Logic**: Supports soft deletes, shared expense tracking, and refund tracking.

**Location**: app/models.py:166-189

---

### 11. RecurringTransaction

**Purpose**: Template for recurring financial transactions with flexible scheduling.

**Table Name**: `recurring_transactions`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique recurring transaction identifier |
| `user_id` | String (UUID) | Foreign Key → `users.id`, Not Null | - | Owner user ID |
| `category_id` | String (UUID) | Foreign Key → `categories.id` | - | Category ID |
| `amount` | Float | Not Null | - | Transaction amount |
| `description` | String | Not Null | - | Transaction description |
| `type` | String | Not Null | - | Transaction type |
| `frequency` | String | Not Null | - | Recurrence frequency (see RecurrenceFrequency enum) |
| `start_date` | DateTime | Not Null | - | Start date for recurrence |
| `next_due_date` | DateTime | Not Null | - | Next scheduled occurrence |
| `date_flexibility` | String | - | `"EXACT"` | Date flexibility (see DateFlexibility enum) |
| `range_start` | Integer | Nullable | - | Start of date range (day of month) |
| `range_end` | Integer | Nullable | - | End of date range (day of month) |
| `preference` | String | Nullable | - | Date preference (earliest, latest, mid) |
| `is_variable_amount` | Boolean | - | `False` | Whether amount varies |
| `estimated_min_amount` | Float | Nullable | - | Minimum estimated amount (if variable) |
| `estimated_max_amount` | Float | Nullable | - | Maximum estimated amount (if variable) |
| `priority` | String | Nullable | - | Transaction priority (see TransactionPriority enum) |
| `is_active` | Boolean | - | `True` | Whether recurrence is active |
| `created_at` | DateTime | - | Current timestamp | Creation timestamp |
| `source_transaction_id` | String (UUID) | Foreign Key → `transactions.id`, Nullable | - | Original transaction (if created from one) |

**Relationships**:
- `category`: Many-to-one with `Category`
- `source_transaction`: Many-to-one with `Transaction`

**Location**: app/models.py:137-164

---

### 12. Goal

**Purpose**: Financial goals with progress tracking and optional category linking.

**Table Name**: `goals`

**Fields**:
| Field | Type | Constraints | Default | Description |
|-------|------|-------------|---------|-------------|
| `id` | String (UUID) | Primary Key | Auto-generated | Unique goal identifier |
| `user_id` | String (UUID) | Foreign Key → `users.id`, Not Null | - | Owner user ID |
| `name` | String | Not Null | - | Goal name |
| `description` | String | - | - | Goal description |
| `target_amount` | Float | Not Null | - | Target amount to achieve |
| `current_amount` | Float | - | `0` | Current progress amount |
| `deadline` | DateTime | Nullable | - | Goal deadline |
| `created_at` | DateTime | - | Current timestamp | Creation timestamp |
| `updated_at` | DateTime | - | Current timestamp | Last update timestamp |
| `status` | String | - | `"active"` | Goal status (active, completed, etc.) |
| `linked_category_id` | String (UUID) | Foreign Key → `categories.id`, Nullable | - | Linked category for tracking |

**Relationships**:
- `user`: Many-to-one with `User`
- `linked_category`: Many-to-one with `Category`

**Location**: app/models.py:210-224

---

## Validation Schemas (Pydantic)

All validation schemas are defined in `/app/schemas.py` and inherit from Pydantic's `BaseModel`.

### User & Authentication Schemas

#### User
**Purpose**: User response schema

**Fields**:
- `id`: str - User ID
- `username`: str - Username

**Location**: app/schemas.py:108-112

---

#### UserCreate
**Purpose**: User registration request

**Fields**:
- `username`: str - Desired username
- `password`: str - Password (will be hashed)

**Location**: app/schemas.py:114-116

---

#### UserLogin
**Purpose**: Login credentials

**Fields**:
- `username`: str - Username
- `password`: str - Password

**Location**: app/schemas.py:118-120

---

#### Token
**Purpose**: JWT token response

**Fields**:
- `access_token`: str - JWT access token
- `token_type`: str - Token type (typically "bearer")

**Location**: app/schemas.py:122-124

---

### Category Schemas

#### Category
**Purpose**: Category response schema

**Fields**:
- `id`: str - Category ID
- `name`: str - Category name

**Location**: app/schemas.py:126-130

---

#### CategoryCreate
**Purpose**: Create new category request

**Fields**:
- `name`: str - Category name

**Location**: app/schemas.py:132-133

---

#### CategoryUpdate
**Purpose**: Update category request

**Fields**:
- `name`: Optional[str] - New category name
- `is_active`: Optional[bool] - Active status

**Location**: app/schemas.py:135-137

---

### Budget Schemas

#### CategoryBudgetCreate
**Purpose**: Create category budget allocation

**Fields**:
- `category_id`: str - Category ID (validated as UUID)
- `budget_amount`: float - Budget amount (0-1,000,000, 2 decimal precision)
- `rollover_enabled`: Optional[bool] - Enable rollover (default: False)

**Validators**:
- `category_id`: Must be valid UUID format
- `budget_amount`: Must be between 0 and 1,000,000, rounded to 2 decimals

**Location**: app/schemas.py:7-25

---

#### CategoryBudgetResponse
**Purpose**: Category budget response with rollover info

**Fields**:
- `id`: str - Category budget ID
- `category_id`: str - Category ID
- `budget_amount`: float - Budget amount
- `rollover_enabled`: bool - Rollover enabled status
- `rollover_amount`: float - Current rollover amount

**Location**: app/schemas.py:27-35

---

#### BudgetCreate
**Purpose**: Create monthly budget with category allocations

**Fields**:
- `year_month`: str - Budget month (format: "YYYY-MM")
- `category_limits`: List[CategoryBudgetCreate] - Category budget allocations

**Location**: app/schemas.py:37-39

---

#### BudgetUpdate
**Purpose**: Update monthly budget

**Fields**:
- `category_limits`: List[CategoryBudgetCreate] - Updated category allocations

**Location**: app/schemas.py:41-42

---

#### BudgetResponse
**Purpose**: Budget response with details

**Fields**:
- `id`: str - Budget ID
- `year_month`: str - Budget month
- `category_limits`: List[CategoryBudgetResponse] - Category allocations with rollover
- `created_at`: datetime - Creation timestamp

**Location**: app/schemas.py:44-50

---

#### BudgetCopyRequest
**Purpose**: Copy budget from one month to another

**Fields**:
- `source_year_month`: str - Source month (format: "YYYY-MM")
- `target_year_month`: str - Target month (format: "YYYY-MM")

**Location**: app/schemas.py:52-54

---

### Project Budget Schemas

#### ProjectBudgetAllocationCreate
**Purpose**: Create category allocation within project budget

**Fields**:
- `category_id`: str - Category ID
- `allocated_amount`: float - Amount allocated

**Location**: app/schemas.py:56-58

---

#### ProjectBudgetAllocationResponse
**Purpose**: Category allocation response

**Fields**:
- `id`: str - Allocation ID
- `category_id`: str - Category ID
- `allocated_amount`: float - Allocated amount

**Location**: app/schemas.py:60-65

---

#### ProjectBudgetCreate
**Purpose**: Create project budget

**Fields**:
- `name`: str - Project name
- `description`: Optional[str] - Project description
- `start_date`: datetime - Project start date
- `end_date`: datetime - Project end date
- `total_amount`: float - Total budget amount
- `category_allocations`: List[ProjectBudgetAllocationCreate] - Category allocations

**Location**: app/schemas.py:67-73

---

#### ProjectBudgetUpdate
**Purpose**: Update project budget

**Fields** (all optional):
- `name`: Optional[str] - New project name
- `description`: Optional[str] - New description
- `start_date`: Optional[datetime] - New start date
- `end_date`: Optional[datetime] - New end date
- `total_amount`: Optional[float] - New total amount
- `category_allocations`: Optional[List[ProjectBudgetAllocationCreate]] - Updated allocations

**Location**: app/schemas.py:75-81

---

#### ProjectBudgetResponse
**Purpose**: Project budget response

**Fields**:
- `id`: str - Project budget ID
- `name`: str - Project name
- `description`: Optional[str] - Description
- `start_date`: datetime - Start date
- `end_date`: datetime - End date
- `total_amount`: float - Total amount
- `created_at`: datetime - Creation timestamp
- `category_allocations`: List[ProjectBudgetAllocationResponse] - Allocations

**Location**: app/schemas.py:83-93

---

#### ProjectBudgetProgress
**Purpose**: Project budget with progress metrics

**Fields**:
- `id`: str - Project budget ID
- `name`: str - Project name
- `description`: Optional[str] - Description
- `start_date`: datetime - Start date
- `end_date`: datetime - End date
- `total_amount`: float - Total amount
- `total_spent`: float - Amount spent so far
- `remaining_amount`: float - Remaining budget
- `progress_percentage`: float - Percentage of budget used
- `days_remaining`: int - Days until end date
- `category_progress`: List[dict] - Per-category progress details

**Location**: app/schemas.py:95-106

---

### Transaction Schemas

#### TransactionCreate
**Purpose**: Create new transaction

**Fields**:
- `category_id`: str - Category ID (validated as UUID)
- `type`: str - Transaction type (income, expense, transfer)
- `description`: str - Transaction description (max 500 chars)
- `amount`: float - Transaction amount (non-zero, -1M to 1M, 2 decimals)
- `occurred_on`: datetime - Transaction date

**Validators**:
- `category_id`: Must be valid UUID format
- `type`: Must be one of: income, expense, transfer
- `description`: Non-empty, max 500 chars, alphanumeric with common punctuation
- `amount`: Non-zero, between -1,000,000 and 1,000,000, rounded to 2 decimals

**Location**: app/schemas.py:185-224

---

#### TransactionUpdate
**Purpose**: Update existing transaction

**Fields** (all optional):
- `id`: str - Transaction ID
- `category_id`: Optional[str] - New category ID
- `type`: Optional[str] - New type
- `description`: Optional[str] - New description
- `amount`: Optional[float] - New amount
- `occurred_on`: Optional[datetime] - New date
- `refunded`: Optional[bool] - Refund status
- `personal_share`: Optional[float] - Personal share amount
- `owed_share`: Optional[float] - Owed share amount
- `share_metadata`: Optional[str] - Additional sharing info
- `recurrence`: Optional[RecurrenceData] - Recurrence configuration

**Location**: app/schemas.py:226-237

---

#### Transaction
**Purpose**: Transaction response schema

**Fields**:
- `id`: str - Transaction ID
- `category_id`: str - Category ID
- `type`: str - Transaction type
- `description`: str - Description
- `amount`: float - Amount
- `occurred_on`: datetime - Transaction date
- `is_deleted`: bool - Soft delete status
- `refunded`: Optional[bool] - Refund status (default: False)
- `personal_share`: Optional[float] - Personal share
- `owed_share`: Optional[float] - Owed share
- `share_metadata`: Optional[str] - Sharing metadata
- `created_at`: Optional[datetime] - Creation timestamp
- `category`: Optional[Category] - Associated category details
- `recurrence`: Optional[RecurrenceData] - Recurrence details

**Location**: app/schemas.py:239-255

---

#### ExpenseResponse
**Purpose**: Simplified expense response

**Fields**:
- `id`: str - Transaction ID
- `category_id`: str - Category ID
- `type`: str - Transaction type
- `description`: str - Description
- `amount`: float - Amount
- `occurred_on`: datetime - Transaction date

**Location**: app/schemas.py:257-265

---

#### ListTransactionsByMonthRequest
**Purpose**: Query parameters for monthly transactions

**Fields**:
- `year`: int - Year
- `month`: int - Month (1-12)

**Location**: app/schemas.py:267-269

---

#### ListExpensesByMonthRequest
**Purpose**: Query parameters for monthly expenses

**Fields**:
- `year`: int - Year
- `month`: int - Month (1-12)

**Location**: app/schemas.py:271-273

---

### Recurring Transaction Schemas

#### RecurringTransactionCreate
**Purpose**: Create recurring transaction

**Fields**:
- `category_id`: str - Category ID
- `amount`: float - Transaction amount
- `description`: str - Description
- `frequency`: str - Recurrence frequency (DAILY, WEEKLY, etc.)
- `start_date`: datetime - Start date
- `date_flexibility`: Optional[str] - Date flexibility (default: "EXACT")

**Location**: app/schemas.py:139-145

---

#### RecurringTransaction
**Purpose**: Recurring transaction response

**Fields**:
- `id`: str - Recurring transaction ID
- `category_id`: str - Category ID
- `amount`: float - Amount
- `description`: str - Description
- `frequency`: str - Frequency
- `start_date`: datetime - Start date
- `next_due_date`: datetime - Next occurrence date
- `date_flexibility`: str - Date flexibility
- `is_active`: bool - Active status
- `category`: Optional[Category] - Category details
- `priority`: Optional[str] - Priority level

**Location**: app/schemas.py:147-160

---

#### RecurringTransactionStatusUpdate
**Purpose**: Update recurring transaction active status

**Fields**:
- `is_active`: bool - New active status

**Location**: app/schemas.py:162-163

---

#### RecurringTransactionUpdate
**Purpose**: Update recurring transaction details

**Fields** (all optional):
- `category_id`: Optional[str] - New category ID
- `amount`: Optional[float] - New amount
- `description`: Optional[str] - New description
- `frequency`: Optional[str] - New frequency
- `start_date`: Optional[datetime] - New start date
- `date_flexibility`: Optional[str] - New date flexibility

**Location**: app/schemas.py:165-171

---

#### RecurrenceData
**Purpose**: Detailed recurrence configuration

**Fields**:
- `id`: Optional[str] - Recurrence ID
- `frequency`: str - Frequency
- `start_date`: datetime - Start date
- `date_flexibility`: Optional[str] - Flexibility (default: "EXACT")
- `range_start`: Optional[int] - Start of date range
- `range_end`: Optional[int] - End of date range
- `preference`: Optional[str] - Date preference (earliest, latest, mid)
- `is_variable_amount`: Optional[bool] - Variable amount flag (default: False)
- `estimated_min_amount`: Optional[float] - Min amount (if variable)
- `estimated_max_amount`: Optional[float] - Max amount (if variable)

**Location**: app/schemas.py:173-183

---

### Allocation Schemas

#### UpcomingExpense
**Purpose**: Represents an upcoming expense for allocation planning

**Fields**:
- `id`: str - Expense ID
- `description`: str - Description
- `amount`: float - Amount
- `due_date`: datetime - Due date
- `category`: str - Category name
- `is_recurring`: bool - Whether it's recurring (default: True)
- `variability_factor`: Optional[float] - Variability factor (default: 0.0)
- `is_variable_amount`: Optional[bool] - Variable amount flag (default: False)
- `estimated_min_amount`: Optional[float] - Min amount
- `estimated_max_amount`: Optional[float] - Max amount

**Location**: app/schemas.py:275-285

---

#### PaycheckAllocation
**Purpose**: Paycheck allocation with assigned expenses

**Fields**:
- `id`: str - Paycheck ID
- `amount`: float - Paycheck amount
- `date`: datetime - Paycheck date
- `source`: str - Income source
- `frequency`: str - Frequency
- `expenses`: List[UpcomingExpense] - Expenses allocated to this paycheck
- `total_allocation_amount`: float - Total allocated to expenses
- `remaining_amount`: float - Remaining after allocations
- `next_paycheck_date`: Optional[datetime] - Next paycheck date

**Location**: app/schemas.py:287-296

---

#### AllocationResponse
**Purpose**: Complete allocation response for a month

**Fields**:
- `paychecks`: List[PaycheckAllocation] - Paychecks with allocations (default: [])
- `income`: float - Total income (default: 0.0)
- `total_expenses`: float - Total expenses (default: 0.0)
- `savings`: float - Total savings (default: 0.0)
- `month`: str - Month identifier
- `details`: dict - Additional details (default: {})

**Location**: app/schemas.py:298-304

---

### Goal Schemas

#### GoalCreate
**Purpose**: Create financial goal

**Fields**:
- `name`: str - Goal name
- `description`: Optional[str] - Goal description
- `target_amount`: float - Target amount
- `deadline`: Optional[datetime] - Goal deadline
- `create_temporary_category`: Optional[bool] - Create linked category (default: False)
- `temporary_category_name`: Optional[str] - Name for temporary category

**Location**: app/schemas.py:306-312

---

#### GoalUpdate
**Purpose**: Update goal details

**Fields** (all optional):
- `name`: Optional[str] - New goal name
- `description`: Optional[str] - New description
- `target_amount`: Optional[float] - New target amount
- `deadline`: Optional[datetime] - New deadline
- `status`: Optional[str] - New status
- `linked_category_id`: Optional[str] - New linked category

**Location**: app/schemas.py:314-320

---

#### GoalResponse
**Purpose**: Goal response with full details

**Fields**:
- `id`: str - Goal ID
- `user_id`: str - Owner user ID
- `name`: str - Goal name
- `description`: Optional[str] - Description
- `target_amount`: float - Target amount
- `current_amount`: float - Current progress
- `deadline`: Optional[datetime] - Deadline
- `created_at`: datetime - Creation timestamp
- `updated_at`: datetime - Last update timestamp
- `status`: str - Status
- `linked_category_id`: Optional[str] - Linked category ID

**Location**: app/schemas.py:322-335

---

## Entity Relationships

### Relationship Diagram

```
User
├── budgets (1:N) → Budget
│   └── category_limits (1:N) → CategoryBudget
│       └── category (N:1) → Category
├── project_budgets (1:N) → ProjectBudget
│   └── category_allocations (1:N) → ProjectBudgetAllocation
│       └── category (N:1) → Category
├── categories (1:N) → Category
│   └── linked_goal (N:1) → Goal
├── transactions (1:N) → Transaction
│   ├── category (N:1) → Category
│   └── recurring_transaction (N:1) → RecurringTransaction
├── recurring_transactions (1:N) → RecurringTransaction
│   ├── category (N:1) → Category
│   └── source_transaction (N:1) → Transaction
└── goals (1:N) → Goal
    └── linked_category (N:1) → Category

Budget
├── rollover_calculations (1:N) → RolloverCalculation
├── rollover_change_log (1:N) → RolloverChangeLog
└── category_limits (1:N) → CategoryBudget

User + Category
└── rollover_configs (N:1) → RolloverConfig
```

### Key Relationships

1. **User is central**: All major entities (budgets, transactions, goals) belong to a user
2. **Categories organize transactions**: Categories can be linked to goals for tracking
3. **Budgets have category-level allocations**: Each budget contains multiple category budget limits
4. **Transactions can be recurring**: Recurring transactions generate actual transactions
5. **Goals can have linked categories**: Track goal progress through category transactions
6. **Project budgets span time periods**: Allocate budget across categories for projects
7. **Rollover is highly tracked**: Multiple entities (Config, Calculation, ChangeLog) track rollover behavior

---

## Enumerations

### RecurrenceFrequency
**Location**: app/models.py:191-197

**Values**:
- `DAILY`: Daily recurrence
- `WEEKLY`: Weekly recurrence
- `BIWEEKLY`: Every two weeks
- `FOUR_WEEKLY`: Every four weeks
- `MONTHLY`: Monthly recurrence
- `YEARLY`: Yearly recurrence

**Usage**: Defines frequency for recurring transactions.

---

### DateFlexibility
**Location**: app/models.py:199-203

**Values**:
- `EXACT`: Exact date required
- `CUSTOM_RANGE`: Custom date range
- `MONTH_RANGE`: Any date within the month
- `SEASONAL`: Seasonal flexibility

**Usage**: Defines how flexible the due date is for recurring transactions.

---

### TransactionPriority
**Location**: app/models.py:205-208

**Values**:
- `LOW`: Low priority
- `MEDIUM`: Medium priority
- `HIGH`: High priority

**Usage**: Defines priority level for recurring transactions.

---

## Validation Rules

### UUID Validation
- **Applied to**: `category_id` in `CategoryBudgetCreate`, `TransactionCreate`
- **Rule**: Must be valid UUID format
- **Error**: "Invalid category ID format"

### Amount Validation

#### Budget Amounts
- **Applied to**: `budget_amount` in `CategoryBudgetCreate`
- **Range**: 0 to 1,000,000
- **Precision**: 2 decimal places
- **Error**: "Budget amount must be between 0 and 1,000,000"

#### Transaction Amounts
- **Applied to**: `amount` in `TransactionCreate`
- **Range**: -1,000,000 to 1,000,000 (excluding 0)
- **Precision**: 2 decimal places
- **Errors**:
  - "Amount cannot be zero"
  - "Amount out of reasonable range (-1M to 1M)"

### Transaction Type Validation
- **Applied to**: `type` in `TransactionCreate`
- **Allowed values**: `income`, `expense`, `transfer`
- **Case**: Converted to lowercase
- **Error**: "Type must be one of: ['income', 'expense', 'transfer']"

### Description Validation
- **Applied to**: `description` in `TransactionCreate`
- **Rules**:
  - Cannot be empty or whitespace only
  - Maximum 500 characters
  - Must match pattern: `^[a-zA-Z0-9\s\-_.,!?()&@#$%]+$`
- **Errors**:
  - "Description cannot be empty"
  - "Description too long (max 500 characters)"
  - "Description contains invalid characters"

### Date Format Validation
- **Applied to**: `year_month` in budgets
- **Format**: `"YYYY-MM"` (e.g., "2024-07")
- **Purpose**: Ensures consistent month representation

---

## Database Constraints

### Unique Constraints

1. **User Username**
   - Table: `users`
   - Field: `username`
   - Ensures unique usernames across the system

2. **Budget per User per Month**
   - Table: `budgets`
   - Fields: `(user_id, year_month)`
   - Ensures one budget per user per month

3. **Rollover Config per User per Category**
   - Table: `rollover_configs`
   - Fields: `(user_id, category_id)`
   - Ensures one rollover configuration per user per category

### Cascade Behaviors

1. **Budget → CategoryBudget**
   - Cascade: `all, delete-orphan`
   - Deleting a budget deletes all associated category budgets

2. **ProjectBudget → ProjectBudgetAllocation**
   - Cascade: `all, delete-orphan`
   - Deleting a project budget deletes all associated allocations

---

## Best Practices

### When Creating Entities

1. **Always validate UUIDs** before passing to foreign key fields
2. **Round monetary amounts** to 2 decimal places
3. **Use transactions** for multi-entity operations (e.g., creating budget with category limits)
4. **Set timestamps** automatically using database defaults
5. **Validate date ranges** for project budgets (end_date > start_date)

### When Querying

1. **Use eager loading** for frequently accessed relationships (use `joinedload`)
2. **Filter out soft-deleted transactions** using `is_deleted = False`
3. **Consider rollover flags** when calculating budget availability
4. **Check is_active** for categories and recurring transactions

### Rollover Management

1. **Always check rollover_needs_recalc** before displaying budget data
2. **Log all rollover changes** in `RolloverChangeLog`
3. **Audit rollover calculations** using `RolloverCalculation`
4. **Respect rollover configuration** (percentage, max amount, expiry)

---

## Additional Notes

### Soft Deletes
- Transactions use soft deletes (`is_deleted` flag) to preserve financial history
- Always filter by `is_deleted = False` when querying active transactions

### Shared Expenses
- Transactions support shared expense tracking via `personal_share`, `owed_share`, and `share_metadata`
- Useful for splitting bills and tracking who owes what

### Variable Amount Recurring Transactions
- Recurring transactions can have variable amounts using `is_variable_amount`, `estimated_min_amount`, and `estimated_max_amount`
- Useful for utilities and other variable recurring expenses

### Goal Progress Tracking
- Goals can be linked to categories via `linked_category_id`
- Transactions in the linked category contribute to goal progress
- Temporary categories can be created automatically when creating goals

---

## Version History

- **Version 1.0** (2025-10-25): Initial documentation covering all models and schemas
