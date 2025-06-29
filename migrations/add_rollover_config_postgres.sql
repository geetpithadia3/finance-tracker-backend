-- Migration: Add rollover configuration fields to category_budgets table
-- REQ-004: Rollover Configuration
-- Database: PostgreSQL

-- Add rollover_unused column
ALTER TABLE category_budgets 
ADD COLUMN IF NOT EXISTS rollover_unused BOOLEAN DEFAULT FALSE;

-- Add rollover_overspend column  
ALTER TABLE category_budgets 
ADD COLUMN IF NOT EXISTS rollover_overspend BOOLEAN DEFAULT FALSE;

-- Add rollover_amount column
ALTER TABLE category_budgets 
ADD COLUMN IF NOT EXISTS rollover_amount REAL DEFAULT 0.0;

-- Update existing records to have default values
UPDATE category_budgets 
SET rollover_unused = FALSE 
WHERE rollover_unused IS NULL;

UPDATE category_budgets 
SET rollover_overspend = FALSE 
WHERE rollover_overspend IS NULL;

UPDATE category_budgets 
SET rollover_amount = 0.0 
WHERE rollover_amount IS NULL;

-- Add comments for documentation
COMMENT ON COLUMN category_budgets.rollover_unused IS 'Whether to rollover unused funds to next month';
COMMENT ON COLUMN category_budgets.rollover_overspend IS 'Whether to deduct overspend from next month';
COMMENT ON COLUMN category_budgets.rollover_amount IS 'Calculated rollover amount from previous month';

-- Verify the changes
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'category_budgets' 
AND column_name IN ('rollover_unused', 'rollover_overspend', 'rollover_amount')
ORDER BY column_name;