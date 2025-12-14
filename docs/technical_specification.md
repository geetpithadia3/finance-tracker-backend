# V2 Technical Specification: API & Database Design

This document serves as the implementation blueprint for the "Domain-Centric" V2 architecture.

## 1. Database Design (Schema)

The database uses a "Double-Entry Lite" approach.

### 1.1 Core Tables

#### `parties`
The single identity table. Abstract "Economic Actor".
```sql
CREATE TABLE parties (
    id UUID PRIMARY KEY,
    type VARCHAR NOT NULL, -- Enum: 'USER', 'HOUSEHOLD'
    name VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `users` (Existing Modified)
Authentication Credential Store.
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    party_id UUID REFERENCES parties(id), -- Link to the Economic Actor
    is_active BOOLEAN DEFAULT TRUE
);
```
**Auth Flow**:
1.  **Signup**: User provides Email/Pass.
2.  **System**:
    - Creates `Party` (Type=USER, Name=Email prefix).
    - Creates `User` linked to that `Party`.
    - Creates Default Accounts (Assets/Expenses) for that `Party`.
3.  **Login**: Returns JWT with `sub=user_id` and `party_id=...`.

#### `accounts`
The unified container for value (Assets and Expenses).
```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY,
    owner_id UUID REFERENCES parties(id),
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL, -- Enum: 'ASSET', 'LIABILITY', 'INCOME', 'EXPENSE'
    parent_id UUID REFERENCES accounts(id), -- For hierarchy (e.g. Living -> Groceries)
    is_active BOOLEAN DEFAULT TRUE,
    currency VARCHAR DEFAULT 'USD'
);
```

#### `transactions`
The event header.
```sql
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    owner_id UUID REFERENCES parties(id), -- Who created/owns this event
    date TIMESTAMP NOT NULL,
    description VARCHAR NOT NULL,
    notes TEXT,
    external_id VARCHAR -- For bank sync (plaid_transaction_id)
);
```

#### `entries`
The ledger movements.
```sql
CREATE TABLE entries (
    id UUID PRIMARY KEY,
    transaction_id UUID REFERENCES transactions(id),
    account_id UUID REFERENCES accounts(id),
    amount DECIMAL(19, 4) NOT NULL, -- Positive = Debit, Negative = Credit (Standard accounting)
    is_reportable BOOLEAN DEFAULT TRUE -- Set to FALSE for refunds/exclusions
);
-- Constraint: Sum of amount for a given transaction_id must equal 0 (or balanced within tolerance)
```

#### `budget_rules`
The monitoring logic.
```sql
CREATE TABLE budget_rules (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    period VARCHAR NOT NULL, -- Enum: 'WEEKLY', 'MONTHLY', 'YEARLY'
    amount_limit DECIMAL(19,4) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE -- Nullable (indefinite)
);
```

#### `recurring_templates`
Automation engine definitions.
```sql
CREATE TABLE recurring_templates (
    id UUID PRIMARY KEY,
    owner_id UUID REFERENCES parties(id),
    name VARCHAR, -- e.g. "Rent", "Netflix"
    cron_expression VARCHAR, -- Or simple enum: 'MONTHLY', 'WEEKLY'
    template_data JSONB NOT NULL, -- Snapshot of the Transaction Payload (Amount, Accounts, Splits)
    next_run_date DATE,
    last_run_date DATE,
    is_active BOOLEAN DEFAULT TRUE
);
```

---

## 2. API Design (REST)

The API implements the "Mullet Strategy": **Simple/Traditional on the outside**, robust on the inside.

### 2.1 Accounts (Categories) Management
We expose "Categories" to the user, but manage "Accounts" internally.

*   `GET /categories`
    *   **Backend**: `SELECT * FROM accounts WHERE type = 'EXPENSE'`
    *   **Response**: `[{id: "uuid", name: "Groceries", parent_id: "...", ...}]`

*   `POST /categories`
    *   **Request**: `{ "name": "Dining", "parent_id": "..." }`
    *   **Backend**: `INSERT INTO accounts (name, type, ...) VALUES ('Dining', 'EXPENSE', ...)`

*   `GET /accounts` (Assets)
    *   **Backend**: `SELECT * FROM accounts WHERE type IN ('ASSET', 'LIABILITY')`
    *   **Use Case**: Managing Checking, Savings, Credit Cards.

### 2.2 Transactions (The Smart Layer)
The API accepts simplified shapes and converts them to Double-Entry rows.

*   `POST /transactions` (Simple Spend)
    *   **Request**: 
        ```json
        {
          "date": "2024-06-15",
          "amount": 50.00,
          "description": "Walmart",
          "category_id": "uuid-groceries", 
          "source_account_id": "uuid-chase-checking"
        }
        ```
    *   **Backend Logic**:
        1.  Create `Transaction(description="Walmart")`
        2.  Create `Entry(account="uuid-chase-checking", amount=-50.00)`
        3.  Create `Entry(account="uuid-groceries", amount=+50.00)`

*   `POST /transactions/split` (Complex / Splits)
    *   **Request**:
        ```json
        {
          "date": "2024-06-15",
          "description": "Target Run",
          "source_account_id": "uuid-chase-checking",
          "total_amount": 100.00,
          "splits": [
            { "category_id": "uuid-groceries", "amount": 60.00 },
            { "category_id": "uuid-household", "amount": 40.00 }
          ]
        }
        ```
    *   **Backend Logic**:
        1.  Create `Transaction`
        2.  Create `Entry(account=Source, amount=-100)`
        3.  Create `Entry(account=Groceries, amount=+60)`
        4.  Create `Entry(account=Household, amount=+40)`

*   `POST /transactions/import` (CSV Bulk)
    *   **Request**: CSV Payload
    *   **Backend Logic**:
        1.  Parse rows.
        2.  For each row, create a Transaction + 1 Entry (Source Account).
        3.  Leave the balancing Entry as "Uncategorized" (Suspense Account) or auto-assign based on rules.

### 2.2 Transactions (Unified API)
One endpoint to rule them all. The `type` determines validation logic.

*   `POST /transactions`
    *   **Request Payload**:
        ```json
        {
          "date": "2024-06-15",
          "description": "Walmart",
          "amount": 50.00,
          "source_account_id": "uuid-chase-checking",
          
          // One of the following discriminators:
          "type": "EXPENSE", // or 'TRANSFER', 'INCOME'
          "destination_account_id": "uuid-groceries" // Can be a Category ID or Account ID
        }
        ```
    *   **Logic by Type**:
        *   **EXPENSE**: Destination is an Expense Account.
        *   **TRANSFER**: Destination is an Asset/Liability Account (e.g., Credit Card).
            *   *Note*: Backend logic is identical (Debit Dest, Credit Source), but validation differs (Transfer ensures you own both accounts).
        *   **INCOME**: Source is an Income Account, Destination is Asset.

*   `POST /recurring` (Create Template)
    *   **Request**:
        ```json
        {
          "frequency": "MONTHLY",
          "start_date": "2024-07-01",
          "transaction_payload": { ... } // Same as POST /transactions
        }
        ```
    *   **Logic**: Creates a `recurring_templates` row. A background scheduler creates the actual `transactions` when due.

*   `POST /transactions/split` (Complex / Splits)
    *   **Request**:
        ```json
        {
          "date": "2024-06-15",
          "description": "Target Run",
          "source_account_id": "uuid-chase-checking",
          "total_amount": 100.00,
          "splits": [
            { "destination_account_id": "uuid-groceries", "amount": 60.00 },
            { "destination_account_id": "uuid-household", "amount": 40.00 }
          ]
        }
        ```


### 2.4 Budgeting
*   `GET /budgets`
    *   **Response**: Returns list of Rules augmented with current status.
    *   **Logic**:
        ```python
        for rule in rules:
             spent = db.query(Sum(Entry.amount))
                     .filter(account_id=rule.account_id)
                     .filter(date >= current_period_start)
             rule.spent = spent
             rule.remaining = (rule.limit * periods_passed) - spent
        ```

### 2.4 Reports
*   `GET /reports/spending`
    *   **Params**: `start_date`, `end_date`
    *   **Backend**:
        ```sql
        SELECT a.name, SUM(e.amount) 
        FROM entries e 
        JOIN accounts a ON e.account_id = a.id
        WHERE a.type = 'EXPENSE' 
        AND e.is_reportable = TRUE
        AND e.date BETWEEN :start AND :end
        GROUP BY a.name
        ```

## 3. Technology Alignment
*   **Framework**: FastAPI (as currently used).
*   **ORM**: SQLAlchemy Async.
*   **Migration**: Alembic.
*   **Validation**: Pydantic v2.

This specification aligns perfectly with the functionalities requested (Splitting, Exclusion, CSV) while maintaining the integrity of the Double-Entry system.
