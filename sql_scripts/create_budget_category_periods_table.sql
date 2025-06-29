-- Create budget_category_periods table
-- This table stores spending tracking for each category within a budget period

CREATE TABLE IF NOT EXISTS budget_category_periods (
    id VARCHAR(36) PRIMARY KEY,
    budget_period_id VARCHAR(36) NOT NULL,
    category_id VARCHAR(36) NOT NULL,
    allocated DECIMAL(15,2) NOT NULL,
    spent DECIMAL(15,2) DEFAULT 0.00,
    carried_over DECIMAL(15,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_budget_cat_periods_period_id FOREIGN KEY (budget_period_id) REFERENCES budget_periods(id) ON DELETE CASCADE,
    CONSTRAINT fk_budget_cat_periods_category_id FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    
    -- Check constraints
    CONSTRAINT chk_budget_cat_periods_allocated CHECK (allocated >= 0),
    CONSTRAINT chk_budget_cat_periods_spent CHECK (spent >= 0),
    
    -- Unique constraint to prevent duplicate category periods
    CONSTRAINT uk_budget_cat_periods_period_category UNIQUE (budget_period_id, category_id)
);

-- Add comment for documentation
COMMENT ON TABLE budget_category_periods IS 'Stores spending tracking for each category within a budget period';

-- Add column comments
COMMENT ON COLUMN budget_category_periods.budget_period_id IS 'Reference to the parent budget period';
COMMENT ON COLUMN budget_category_periods.category_id IS 'Reference to the category being tracked';
COMMENT ON COLUMN budget_category_periods.allocated IS 'Amount allocated to this category for this period';
COMMENT ON COLUMN budget_category_periods.spent IS 'Amount spent in this category during this period';
COMMENT ON COLUMN budget_category_periods.carried_over IS 'Amount carried over from previous period for this category';