-- Manual PostgreSQL Migration for Rollover Configuration
-- REQ-004: Rollover Configuration
-- Run this directly in your PostgreSQL client (psql, pgAdmin, etc.)

-- First, check if the columns already exist
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'category_budgets' 
AND column_name IN ('rollover_unused', 'rollover_overspend', 'rollover_amount');

-- Add the rollover columns (IF NOT EXISTS prevents errors if already added)
ALTER TABLE category_budgets 
ADD COLUMN IF NOT EXISTS rollover_unused BOOLEAN DEFAULT FALSE;

ALTER TABLE category_budgets 
ADD COLUMN IF NOT EXISTS rollover_overspend BOOLEAN DEFAULT FALSE;

ALTER TABLE category_budgets 
ADD COLUMN IF NOT EXISTS rollover_amount REAL DEFAULT 0.0;

-- Set default values for existing records
UPDATE category_budgets 
SET rollover_unused = FALSE 
WHERE rollover_unused IS NULL;

UPDATE category_budgets 
SET rollover_overspend = FALSE 
WHERE rollover_overspend IS NULL;

UPDATE category_budgets 
SET rollover_amount = 0.0 
WHERE rollover_amount IS NULL;

-- Verify the migration worked
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'category_budgets' 
AND column_name IN ('rollover_unused', 'rollover_overspend', 'rollover_amount')
ORDER BY column_name;

-- Check a few sample records to make sure defaults were set
SELECT id, budget_amount, rollover_unused, rollover_overspend, rollover_amount 
FROM category_budgets 
LIMIT 5;