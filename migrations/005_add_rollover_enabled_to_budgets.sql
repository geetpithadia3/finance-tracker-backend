-- Migration 005: Add rollover_enabled column to budgets table

-- Add rollover_enabled column to budgets table
ALTER TABLE budgets ADD COLUMN IF NOT EXISTS rollover_enabled BOOLEAN DEFAULT TRUE;

-- Update existing records to have rollover enabled by default
UPDATE budgets SET rollover_enabled = TRUE WHERE rollover_enabled IS NULL;

-- Add comment for clarity
COMMENT ON COLUMN budgets.rollover_enabled IS 'Whether unused budget amounts should roll over to the next month';