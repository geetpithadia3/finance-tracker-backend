-- Migration 003: Add Budget Plans and Periods Tables

-- Create budget plans table
CREATE TABLE IF NOT EXISTS budget_plans (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    category_id VARCHAR NOT NULL REFERENCES categories(id),
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL DEFAULT 'REGULAR',
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    recurrence VARCHAR NOT NULL DEFAULT 'MONTHLY',
    rollover_policy VARCHAR NOT NULL DEFAULT 'NONE',
    max_amount REAL NOT NULL,
    alert_thresholds TEXT,
    tags TEXT,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create budget periods table
CREATE TABLE IF NOT EXISTS budget_periods (
    id VARCHAR PRIMARY KEY,
    plan_id VARCHAR NOT NULL REFERENCES budget_plans(id) ON DELETE CASCADE,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    allocated REAL NOT NULL,
    spent REAL DEFAULT 0.0,
    carried_over REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_budget_plans_user_id ON budget_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_budget_plans_category_id ON budget_plans(category_id);
CREATE INDEX IF NOT EXISTS idx_budget_plans_is_archived ON budget_plans(is_archived);
CREATE INDEX IF NOT EXISTS idx_budget_plans_type ON budget_plans(type);
CREATE INDEX IF NOT EXISTS idx_budget_plans_start_date ON budget_plans(start_date);
CREATE INDEX IF NOT EXISTS idx_budget_plans_end_date ON budget_plans(end_date);

CREATE INDEX IF NOT EXISTS idx_budget_periods_plan_id ON budget_periods(plan_id);
CREATE INDEX IF NOT EXISTS idx_budget_periods_period_start ON budget_periods(period_start);
CREATE INDEX IF NOT EXISTS idx_budget_periods_period_end ON budget_periods(period_end);

-- Add constraint to prevent overlapping periods for the same plan
CREATE UNIQUE INDEX IF NOT EXISTS idx_budget_periods_unique_period 
ON budget_periods(plan_id, period_start, period_end);

-- Add constraint to prevent overlapping budget plans for the same category
-- This will be enforced in the application logic due to complexity of the constraint