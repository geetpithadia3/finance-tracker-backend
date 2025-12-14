# Transaction API V2 - Request & Response Format

## Overview
After the V2 migration to double-entry accounting, the Transaction API has been enhanced to support advanced features while maintaining backward compatibility.

## Request Format

### Endpoint
```
POST /api/transactions
```

### Headers
```
Authorization: Bearer <token>
Content-Type: application/json
```

### Request Body Schema (`TransactionCreate`)

#### Core Fields (Required)
```json
{
  "category_id": "string (UUID)",
  "type": "string (CREDIT|DEBIT|TRANSFER)",
  "description": "string (max 500 chars)",
  "amount": "float (non-zero, -1M to 1M)",
  "occurred_on": "datetime (ISO 8601)"
}
```

#### Optional Fields
```json
{
  "source_account_id": "string (UUID) | null",
  "destination_account_id": "string (UUID) | null",
  "splits": "array | null",
  "share": "object | null"
}
```

## V2 Feature Fields

### 1. Explicit Source (`source_account_id`)
Specify which asset/liability account to use for payment.

**Example: Pay with Credit Card**
```json
{
  "category_id": "expense-category-uuid",
  "type": "DEBIT",
  "description": "Amazon Purchase",
  "amount": 75.00,
  "occurred_on": "2024-01-15T10:00:00",
  "source_account_id": "amex-card-uuid"
}
```

**Default Behavior**: If omitted, uses "Cash" account.

### 2. Transfers (`type: TRANSFER`)
Move money between accounts.

**Example: Transfer to Savings**
```json
{
  "category_id": "savings-account-uuid",
  "type": "TRANSFER",
  "description": "Monthly Savings",
  "amount": 500.00,
  "occurred_on": "2024-01-15T10:00:00",
  "source_account_id": "checking-account-uuid",
  "destination_account_id": "savings-account-uuid"
}
```

### 3. Split Transactions (`splits`)
Divide a single transaction across multiple categories.

**Example: Target Run (Groceries + Clothes)**
```json
{
  "category_id": "groceries-uuid",
  "type": "DEBIT",
  "description": "Target Run",
  "amount": 150.00,
  "occurred_on": "2024-01-15T10:00:00",
  "splits": [
    {"category_id": "groceries-uuid", "amount": 100.00},
    {"category_id": "clothing-uuid", "amount": 50.00}
  ]
}
```

**Validation**: Sum of splits must equal total amount.

### 4. Personal Share (`share`)
Track reimbursable expenses with flexible calculation methods.

**Share Config Object**
```json
{
  "method": "FIXED | PERCENTAGE | EQUAL",
  "value": "float"
}
```

#### Method: FIXED
Specify exact personal amount.
```json
{
  "category_id": "dinner-uuid",
  "type": "DEBIT",
  "description": "Team Dinner",
  "amount": 200.00,
  "occurred_on": "2024-01-15T20:00:00",
  "share": {
    "method": "FIXED",
    "value": 80.00
  }
}
```
**Result**: $80 → Expense, $120 → Reimbursable (Asset)

#### Method: PERCENTAGE
Specify personal share as percentage.
```json
{
  "share": {
    "method": "PERCENTAGE",
    "value": 40
  }
}
```
**Result**: 40% → Expense, 60% → Reimbursable

#### Method: EQUAL
Split equally among N people.
```json
{
  "share": {
    "method": "EQUAL",
    "value": 3
  }
}
```
**Result**: 1/3 → Expense, 2/3 → Reimbursable

#### Legacy: `personal_amount`
Still supported for backward compatibility.
```json
{
  "personal_amount": 80.00
}
```

## Response Format

### Success Response (201 Created)
```json
{
  "id": "transaction-uuid",
  "user_id": "user-uuid",
  "category_id": "category-uuid",
  "type": "EXPENSE",
  "description": "Transaction description",
  "amount": 150.00,
  "occurred_on": "2024-01-15T10:00:00",
  "created_at": "2024-01-15T10:00:00",
  "category": {
    "id": "category-uuid",
    "name": "Groceries",
    "user_id": "user-uuid",
    "household_id": null
  }
}
```

### Response Schema (`Transaction`)
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Transaction UUID |
| `user_id` | string | Owner user UUID |
| `category_id` | string | Primary category UUID |
| `type` | string | Transaction type |
| `description` | string | Transaction description |
| `amount` | float | Transaction amount |
| `occurred_on` | datetime | Transaction date |
| `created_at` | datetime? | Creation timestamp |
| `category` | object? | Category details |

## Validation Rules

### `category_id`
- Must be valid UUID format
- Must exist in user's accounts

### `type`
- Allowed: `CREDIT`, `DEBIT`, `TRANSFER`
- Case insensitive (auto-uppercased)

### `description`
- Required, non-empty
- Max 500 characters
- Allowed chars: `a-zA-Z0-9 -_.,!?()&@#$%`

### `amount`
- Cannot be zero
- Range: -1,000,000 to 1,000,000
- Auto-rounded to 2 decimal places

### `source_account_id`
- Must be valid UUID if provided
- Must be owned by user
- Must be ASSET or LIABILITY type

### `splits`
- Sum must equal `amount` (±0.01 tolerance)
- Each split must have valid `category_id` and `amount`

### `share`
- `method` must be: FIXED, PERCENTAGE, or EQUAL
- `value` must be positive
- For PERCENTAGE: 0-100
- For EQUAL: count of people
- Calculated personal amount must be ≤ total amount

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid category ID format"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## V2 Internal Behavior

### Double-Entry Ledger
All transactions create balanced ledger entries:

**Simple Expense**
```
Debit:  Expense Account (+$150)
Credit: Cash Account    (-$150)
```

**With Explicit Source**
```
Debit:  Expense Account      (+$75)
Credit: Credit Card Account  (-$75)
```

**Split Transaction**
```
Debit:  Groceries (+$100)
Debit:  Clothing  (+$50)
Credit: Cash      (-$150)
```

**Personal Share**
```
Debit:  Expense      (+$80)
Debit:  Reimbursable (+$120)
Credit: Cash         (-$200)
```

**Transfer**
```
Debit:  Savings Account  (+$500)
Credit: Checking Account (-$500)
```

## Migration Notes

### Removed Legacy Fields
- `goal_id` - Goals feature not yet implemented in V2
- `personal_amount` - Replaced by `share` object
- `is_deleted`, `refunded` - Soft delete not implemented
- `personal_share`, `owed_share`, `share_metadata` - V1 fields
- `recurrence` - Recurring transactions not yet implemented

### Clean V2 Schema
The API now uses a clean, purpose-built schema focused on double-entry accounting principles.
1. Multi-source payments (Credit Card, Cash, etc.)
2. Inter-account transfers
3. Split transactions across categories
4. Reimbursable expense tracking
5. Auto-categorization via rules

## Example Use Cases

### Use Case 1: Business Expense
```json
{
  "category_id": "meals-uuid",
  "type": "DEBIT",
  "description": "Client Lunch",
  "amount": 120.00,
  "occurred_on": "2024-01-15T12:30:00",
  "source_account_id": "amex-uuid",
  "share": {
    "method": "PERCENTAGE",
    "value": 100
  }
}
```
**Result**: Full amount reimbursable, paid by Amex.

### Use Case 2: Shared Vacation
```json
{
  "category_id": "vacation-uuid",
  "type": "DEBIT",
  "description": "Hotel (4 people)",
  "amount": 800.00,
  "occurred_on": "2024-01-15T15:00:00",
  "share": {
    "method": "EQUAL",
    "value": 4
  }
}
```
**Result**: $200 personal, $600 reimbursable.

### Use Case 3: Multi-Category Purchase
```json
{
  "category_id": "groceries-uuid",
  "type": "DEBIT",
  "description": "Costco Run",
  "amount": 300.00,
  "occurred_on": "2024-01-15T16:00:00",
  "splits": [
    {"category_id": "groceries-uuid", "amount": 200.00},
    {"category_id": "household-uuid", "amount": 100.00}
  ]
}
```
**Result**: Properly categorized across two expense types.
