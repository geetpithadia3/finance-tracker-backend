-- Migration: Add Project Budget tables
-- Description: Creates project_budgets and project_budget_allocations tables for REQ-002

-- Create project_budgets table
CREATE TABLE IF NOT EXISTS project_budgets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    total_amount REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- Create project_budget_allocations table
CREATE TABLE IF NOT EXISTS project_budget_allocations (
    id TEXT PRIMARY KEY,
    project_budget_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    allocated_amount REAL NOT NULL,
    FOREIGN KEY (project_budget_id) REFERENCES project_budgets (id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_project_budgets_user_id ON project_budgets(user_id);
CREATE INDEX IF NOT EXISTS idx_project_budgets_dates ON project_budgets(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_project_budget_allocations_project_id ON project_budget_allocations(project_budget_id);
CREATE INDEX IF NOT EXISTS idx_project_budget_allocations_category_id ON project_budget_allocations(category_id);