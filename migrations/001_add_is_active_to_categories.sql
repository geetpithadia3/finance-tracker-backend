-- Migration: Add is_active column to categories table
-- Date: 2025-06-14
-- Database: PostgreSQL

-- Add is_active column with default value of true
ALTER TABLE categories ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;

-- Update existing categories to be active by default (PostgreSQL syntax)
UPDATE categories SET is_active = true WHERE is_active IS NULL;