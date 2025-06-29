-- Add new fields to recurring_transactions table
ALTER TABLE recurring_transactions 
ADD COLUMN range_start INTEGER,
ADD COLUMN range_end INTEGER,
ADD COLUMN preference TEXT,
ADD COLUMN source_transaction_id TEXT,
ADD CONSTRAINT fk_recurring_source_transaction 
FOREIGN KEY (source_transaction_id) REFERENCES transactions(id);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_recurring_source_transaction 
ON recurring_transactions(source_transaction_id);