-- Create budget_plans table (Updated for 1:many relationship)
-- This table stores the main budget plan configurations that can span multiple categories

CREATE TABLE IF NOT EXISTS budget_plans (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'REGULAR',
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NULL,
    recurrence VARCHAR(20) NOT NULL DEFAULT 'MONTHLY',
    rollover_policy VARCHAR(20) NOT NULL DEFAULT 'NONE',
    total_amount DECIMAL(15,2) NOT NULL,
    alert_thresholds TEXT NULL,
    tags TEXT NULL,
    is_archived BOOLEAN DEFAULT FALSE,
    
    -- Goal-based budget specific fields
    goal_target_amount DECIMAL(15,2) NULL,
    goal_target_date TIMESTAMP NULL,
    goal_current_amount DECIMAL(15,2) DEFAULT 0.00,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_budget_plans_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    -- Check constraints
    CONSTRAINT chk_budget_plans_type CHECK (type IN ('REGULAR', 'TEMPORARY', 'GOAL_BASED')),
    CONSTRAINT chk_budget_plans_recurrence CHECK (recurrence IN ('MONTHLY', 'QUARTERLY', 'NONE')),
    CONSTRAINT chk_budget_plans_rollover_policy CHECK (rollover_policy IN ('NONE', 'REMAINING', 'OVERRUN', 'BOTH')),
    CONSTRAINT chk_budget_plans_total_amount CHECK (total_amount > 0),
    CONSTRAINT chk_budget_plans_goal_target CHECK (
        (type != 'GOAL_BASED') OR 
        (type = 'GOAL_BASED' AND goal_target_amount > 0 AND goal_target_date IS NOT NULL)
    ),
    CONSTRAINT chk_budget_plans_goal_current CHECK (goal_current_amount >= 0)
);

-- Add comment for documentation
COMMENT ON TABLE budget_plans IS 'Stores budget plan configurations supporting multiple categories, different types, recurrence patterns, and goal-based budgeting';

-- Add column comments
COMMENT ON COLUMN budget_plans.name IS 'Display name for the budget plan';
COMMENT ON COLUMN budget_plans.description IS 'Optional detailed description of the budget purpose';
COMMENT ON COLUMN budget_plans.type IS 'Budget type: REGULAR (recurring), TEMPORARY (one-time), GOAL_BASED (savings target)';
COMMENT ON COLUMN budget_plans.recurrence IS 'How often the budget repeats: MONTHLY, QUARTERLY, or NONE for one-time budgets';
COMMENT ON COLUMN budget_plans.rollover_policy IS 'How unused/overspent amounts are handled: NONE, REMAINING, OVERRUN, or BOTH';
COMMENT ON COLUMN budget_plans.total_amount IS 'Total budget amount across all categories';
COMMENT ON COLUMN budget_plans.alert_thresholds IS 'JSON array of percentage thresholds for alerts, e.g., "[80, 100]"';
COMMENT ON COLUMN budget_plans.tags IS 'JSON array of tags for filtering expenses, e.g., ["vacation", "emergency"]';
COMMENT ON COLUMN budget_plans.is_archived IS 'Soft delete flag - archived budgets are hidden from active views';
COMMENT ON COLUMN budget_plans.goal_target_amount IS 'Target amount for goal-based budgets (required for GOAL_BASED type)';
COMMENT ON COLUMN budget_plans.goal_target_date IS 'Target completion date for goal-based budgets (required for GOAL_BASED type)';
COMMENT ON COLUMN budget_plans.goal_current_amount IS 'Current progress amount for goal-based budgets';