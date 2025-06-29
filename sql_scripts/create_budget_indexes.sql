-- Create indexes for enhanced budget system tables
-- These indexes improve query performance for common operations

-- Budget Plans Indexes
CREATE INDEX IF NOT EXISTS idx_budget_plans_user_id ON budget_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_budget_plans_is_archived ON budget_plans(is_archived);
CREATE INDEX IF NOT EXISTS idx_budget_plans_type ON budget_plans(type);
CREATE INDEX IF NOT EXISTS idx_budget_plans_start_date ON budget_plans(start_date);
CREATE INDEX IF NOT EXISTS idx_budget_plans_end_date ON budget_plans(end_date);
CREATE INDEX IF NOT EXISTS idx_budget_plans_active_dates ON budget_plans(start_date, end_date, is_archived);
CREATE INDEX IF NOT EXISTS idx_budget_plans_goal_target_date ON budget_plans(goal_target_date);

-- Budget Category Allocations Indexes
CREATE INDEX IF NOT EXISTS idx_budget_allocations_plan_id ON budget_category_allocations(budget_plan_id);
CREATE INDEX IF NOT EXISTS idx_budget_allocations_category_id ON budget_category_allocations(category_id);

-- Budget Periods Indexes
CREATE INDEX IF NOT EXISTS idx_budget_periods_plan_id ON budget_periods(plan_id);
CREATE INDEX IF NOT EXISTS idx_budget_periods_period_start ON budget_periods(period_start);
CREATE INDEX IF NOT EXISTS idx_budget_periods_period_end ON budget_periods(period_end);
CREATE INDEX IF NOT EXISTS idx_budget_periods_date_range ON budget_periods(period_start, period_end);

-- Budget Category Periods Indexes
CREATE INDEX IF NOT EXISTS idx_budget_cat_periods_period_id ON budget_category_periods(budget_period_id);
CREATE INDEX IF NOT EXISTS idx_budget_cat_periods_category_id ON budget_category_periods(category_id);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_budget_plans_user_active ON budget_plans(user_id, is_archived, type);
CREATE INDEX IF NOT EXISTS idx_budget_periods_plan_dates ON budget_periods(plan_id, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_budget_allocations_plan_category ON budget_category_allocations(budget_plan_id, category_id);

-- Unique constraint to prevent overlapping periods for the same plan
CREATE UNIQUE INDEX IF NOT EXISTS idx_budget_periods_unique_period 
ON budget_periods(plan_id, period_start, period_end);

-- Performance indexes for goal-based budget queries
CREATE INDEX IF NOT EXISTS idx_budget_plans_goals_active ON budget_plans(user_id, type, is_archived) 
WHERE type = 'GOAL_BASED';

-- Index comments for documentation
COMMENT ON INDEX idx_budget_plans_user_id IS 'Fast lookup of budget plans by user';
COMMENT ON INDEX idx_budget_plans_active_dates IS 'Optimizes queries for active budgets within date ranges';
COMMENT ON INDEX idx_budget_periods_unique_period IS 'Prevents duplicate periods for the same budget plan';
COMMENT ON INDEX idx_budget_allocations_plan_id IS 'Fast lookup of category allocations by budget plan';
COMMENT ON INDEX idx_budget_cat_periods_period_id IS 'Fast lookup of category periods by budget period';
COMMENT ON INDEX idx_budget_plans_goals_active IS 'Optimized index for goal-based budget queries';