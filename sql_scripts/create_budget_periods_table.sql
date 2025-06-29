-- Create budget_periods table (Updated for multi-category support)
-- This table stores individual budget periods for each budget plan with aggregate totals

CREATE TABLE IF NOT EXISTS budget_periods (
    id VARCHAR(36) PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    total_allocated DECIMAL(15,2) NOT NULL,
    total_spent DECIMAL(15,2) DEFAULT 0.00,
    total_carried_over DECIMAL(15,2) DEFAULT 0.00,
    
    -- Goal-based budget specific fields
    goal_contribution DECIMAL(15,2) DEFAULT 0.00,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_budget_periods_plan_id FOREIGN KEY (plan_id) REFERENCES budget_plans(id) ON DELETE CASCADE,
    
    -- Check constraints
    CONSTRAINT chk_budget_periods_total_allocated CHECK (total_allocated >= 0),
    CONSTRAINT chk_budget_periods_total_spent CHECK (total_spent >= 0),
    CONSTRAINT chk_budget_periods_goal_contribution CHECK (goal_contribution >= 0),
    CONSTRAINT chk_budget_periods_dates CHECK (period_end >= period_start)
);

-- Add comment for documentation
COMMENT ON TABLE budget_periods IS 'Stores individual budget periods with aggregate spending tracking across all categories';

-- Add column comments
COMMENT ON COLUMN budget_periods.plan_id IS 'Reference to the parent budget plan';
COMMENT ON COLUMN budget_periods.period_start IS 'Start date of this budget period (inclusive)';
COMMENT ON COLUMN budget_periods.period_end IS 'End date of this budget period (inclusive)';
COMMENT ON COLUMN budget_periods.total_allocated IS 'Total amount allocated for this period across all categories (includes rollovers)';
COMMENT ON COLUMN budget_periods.total_spent IS 'Total amount spent during this period across all categories';
COMMENT ON COLUMN budget_periods.total_carried_over IS 'Total amount carried over from previous period across all categories';
COMMENT ON COLUMN budget_periods.goal_contribution IS 'Amount contributed to goal for goal-based budgets (unspent amount)';