-- Migration 004: Add missing user fields
-- This migration adds username, password, created_at, and is_active fields to the users table

-- Add username column (nullable first to allow existing records)
ALTER TABLE users ADD COLUMN username TEXT;

-- Add password column (nullable first to allow existing records) 
ALTER TABLE users ADD COLUMN password TEXT;

-- Add created_at column with default value
ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add is_active column with default value
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;

-- For existing users, set username to email (as a fallback)
UPDATE users SET username = email WHERE username IS NULL;

-- For existing users, set a default password (they'll need to reset)
UPDATE users SET password = '$2b$12$defaulthashedpassword' WHERE password IS NULL;

-- Now make username and password NOT NULL
-- Note: In production, you'd want to handle existing users more carefully
ALTER TABLE users ALTER COLUMN username SET NOT NULL;
ALTER TABLE users ALTER COLUMN password SET NOT NULL;

-- Add unique constraint to username
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- Verify the table structure
-- SELECT * FROM pragma_table_info('users');