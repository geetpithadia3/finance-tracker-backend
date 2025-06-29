# Budget System SQL Scripts

This directory contains SQL scripts to set up and manage the enhanced budget system for the personal finance application.

## 📁 Files Overview

### Core Table Creation
- **`create_budget_plans_table.sql`** - Creates the main budget plans table
- **`create_budget_periods_table.sql`** - Creates the budget periods table  
- **`create_budget_indexes.sql`** - Creates performance indexes and constraints

### Data Management
- **`sample_budget_data.sql`** - Sample data for testing and development
- **`budget_queries.sql`** - Useful queries for reporting and administration

## 🚀 Setup Instructions

### 1. Create Tables (Required)
Run these scripts in order to set up the budget system:

```sql
-- Step 1: Create budget plans table
\i create_budget_plans_table.sql

-- Step 2: Create budget periods table  
\i create_budget_periods_table.sql

-- Step 3: Create indexes for performance
\i create_budget_indexes.sql
```

### 2. Add Sample Data (Optional)
For testing and development:

```sql
-- Add sample budget data (update user_id and category_id values first)
\i sample_budget_data.sql
```

### 3. Use Administrative Queries (As Needed)
```sql
-- Run reporting and management queries
\i budget_queries.sql
```

## 📊 Table Structure

### `budget_plans`
Main table storing budget configurations:
- **id**: Unique identifier (VARCHAR(36))
- **user_id**: Reference to users table
- **category_id**: Reference to categories table  
- **name**: Budget display name
- **type**: REGULAR | TEMPORARY | GOAL_BASED
- **start_date/end_date**: Budget validity period
- **recurrence**: MONTHLY | QUARTERLY | NONE
- **rollover_policy**: NONE | REMAINING | OVERRUN | BOTH
- **max_amount**: Budget limit per period
- **alert_thresholds**: JSON array of alert percentages
- **tags**: JSON array of tags for filtering
- **is_archived**: Soft delete flag

### `budget_periods`  
Table storing individual budget periods:
- **id**: Unique identifier (VARCHAR(36))
- **plan_id**: Reference to budget_plans table
- **period_start/period_end**: Period date range
- **allocated**: Total amount for this period (includes rollovers)
- **spent**: Amount spent (calculated from transactions)
- **carried_over**: Amount carried from previous period

## 🔧 Database Compatibility

These scripts are designed for:
- **PostgreSQL** (primary target)
- **MySQL** (with minor syntax adjustments)
- **SQLite** (for development - may need data type adjustments)

### PostgreSQL Specific Features Used:
- DECIMAL(15,2) for monetary values
- TEXT data type for JSON storage
- TIMESTAMP data type
- CASCADE foreign key constraints
- Table and column comments

### For MySQL Compatibility:
- Change TIMESTAMP to DATETIME if needed
- Ensure proper charset (utf8mb4) for TEXT fields
- Verify foreign key constraint syntax

### For SQLite Compatibility:
- Change DECIMAL to REAL
- Remove foreign key constraints (enforce in application)
- Remove comments (not supported)

## 🔍 Key Indexes Created

Performance indexes for common queries:
- User-based budget lookups
- Category-based budget searches  
- Date range queries for active budgets
- Period overlap prevention (unique constraint)
- Composite indexes for complex filters

## 📈 Sample Queries Included

The `budget_queries.sql` file includes:

1. **Active budget overview** - Current budget status for a user
2. **Budget alerts** - Budgets exceeding thresholds  
3. **Monthly summaries** - Spending by category
4. **Historical performance** - Budget trends over time
5. **Period management** - Find budgets needing new periods
6. **Transaction tracking** - Expenses affecting specific budgets
7. **Maintenance queries** - Cleanup archived data

## ⚠️ Important Notes

### Before Running Sample Data:
1. Update `user-123-456` with actual user IDs from your users table
2. Update category IDs (`cat-groceries-001`, etc.) with real category IDs
3. Adjust dates to match your application's current date

### Security Considerations:
- All foreign key constraints include CASCADE deletes
- Unique constraints prevent data conflicts
- Check constraints validate data integrity
- Soft deletes (is_archived) preserve data relationships

### Performance Notes:
- Indexes are optimized for common query patterns
- Large deployments may need additional indexes
- Consider partitioning budget_periods by date for very large datasets

## 🧪 Testing Your Setup

After running the scripts, verify with:

```sql
-- Check table creation
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('budget_plans', 'budget_periods');

-- Check indexes
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('budget_plans', 'budget_periods');

-- Test sample data (if loaded)
SELECT COUNT(*) as plan_count FROM budget_plans;
SELECT COUNT(*) as period_count FROM budget_periods;
```

## 🔄 Integration with Application

These tables integrate with existing application tables:
- **users** - Budget plans belong to users
- **categories** - Budgets track spending by category
- **transactions** - Expense transactions update budget spending

The application automatically:
- Creates new budget periods for recurring budgets
- Updates spending amounts when transactions change
- Calculates rollover amounts based on policies
- Generates alerts when thresholds are exceeded