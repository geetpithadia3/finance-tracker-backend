"""
Migration: Add rollover configuration fields to category_budgets table
REQ-004: Rollover Configuration
"""

import sqlite3
import os

def migrate():
    """Add rollover configuration fields to category_budgets table"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'finance_tracker.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(category_budgets)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'rollover_unused' not in columns:
            print("Adding rollover_unused column...")
            cursor.execute("""
                ALTER TABLE category_budgets 
                ADD COLUMN rollover_unused BOOLEAN DEFAULT 0
            """)
        
        if 'rollover_overspend' not in columns:
            print("Adding rollover_overspend column...")
            cursor.execute("""
                ALTER TABLE category_budgets 
                ADD COLUMN rollover_overspend BOOLEAN DEFAULT 0
            """)
            
        if 'rollover_amount' not in columns:
            print("Adding rollover_amount column...")
            cursor.execute("""
                ALTER TABLE category_budgets 
                ADD COLUMN rollover_amount REAL DEFAULT 0.0
            """)
        
        conn.commit()
        print("Rollover configuration migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()