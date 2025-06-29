-- Create budget_category_allocations table
-- This table stores how budget amounts are allocated across different categories

CREATE TABLE IF NOT EXISTS budget_category_allocations (
    id VARCHAR(36) PRIMARY KEY,
    budget_plan_id VARCHAR(36) NOT NULL,
    category_id VARCHAR(36) NOT NULL,
    allocated_amount DECIMAL(15,2) NOT NULL,
    percentage_of_total DECIMAL(5,2) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraints
    CONSTRAINT fk_budget_allocations_plan_id FOREIGN KEY (budget_plan_id) REFERENCES budget_plans(id) ON DELETE CASCADE,
    CONSTRAINT fk_budget_allocations_category_id FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    
    -- Check constraints
    CONSTRAINT chk_budget_allocations_amount CHECK (allocated_amount >= 0),
    CONSTRAINT chk_budget_allocations_percentage CHECK (percentage_of_total IS NULL OR (percentage_of_total >= 0 AND percentage_of_total <= 100)),
    
    -- Unique constraint to prevent duplicate allocations
    CONSTRAINT uk_budget_allocations_plan_category UNIQUE (budget_plan_id, category_id)
);

-- Add comment for documentation
COMMENT ON TABLE budget_category_allocations IS 'Stores how budget amounts are allocated across different categories within a budget plan';

-- Add column comments
COMMENT ON COLUMN budget_category_allocations.budget_plan_id IS 'Reference to the parent budget plan';
COMMENT ON COLUMN budget_category_allocations.category_id IS 'Reference to the category receiving the allocation';
COMMENT ON COLUMN budget_category_allocations.allocated_amount IS 'Amount allocated to this category';
COMMENT ON COLUMN budget_category_allocations.percentage_of_total IS 'Optional percentage of total budget allocated to this category';