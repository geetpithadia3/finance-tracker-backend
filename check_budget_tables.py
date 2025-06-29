#!/usr/bin/env python3
"""
Quick script to check if budget_plans and budget_periods tables exist and create them if needed.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models import BudgetPlan, BudgetPeriod
from sqlalchemy import text, inspect

def check_and_create_tables():
    """Check if budget plan tables exist and create them if they don't"""
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print("Existing tables:", existing_tables)
    
    # Check if budget_plans table exists
    if 'budget_plans' not in existing_tables:
        print("❌ budget_plans table does not exist")
    else:
        print("✅ budget_plans table exists")
        
    # Check if budget_periods table exists
    if 'budget_periods' not in existing_tables:
        print("❌ budget_periods table does not exist")
    else:
        print("✅ budget_periods table exists")
    
    # Create tables if they don't exist
    print("\nCreating all tables from models...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully")
        
        # Check again
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        print("Tables after creation:", existing_tables)
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    check_and_create_tables()