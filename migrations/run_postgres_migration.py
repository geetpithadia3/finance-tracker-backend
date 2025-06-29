#!/usr/bin/env python3
"""
PostgreSQL Migration Runner for Rollover Configuration
REQ-004: Rollover Configuration
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.config import settings
    DATABASE_URL = settings.database_url
except ImportError:
    # Fallback - you can set your PostgreSQL connection string here
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://username:password@localhost:5432/database_name")

def run_migration():
    """Run the PostgreSQL migration for rollover configuration"""
    
    print("Running PostgreSQL migration for rollover configuration...")
    print(f"Database URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('//')[1], '****')}")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Read the SQL migration file
        migration_file = os.path.join(os.path.dirname(__file__), "add_rollover_config_postgres.sql")
        
        if not os.path.exists(migration_file):
            print(f"Error: Migration file not found: {migration_file}")
            return False
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Split SQL statements (PostgreSQL can handle multiple statements)
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        # Execute migration
        with engine.connect() as conn:
            with conn.begin():
                print("Starting transaction...")
                
                for i, statement in enumerate(statements):
                    if statement.upper().startswith('SELECT'):
                        # For SELECT statements, fetch and display results
                        print(f"Executing verification query {i+1}...")
                        result = conn.execute(text(statement))
                        rows = result.fetchall()
                        if rows:
                            print("Migration verification results:")
                            for row in rows:
                                print(f"  Column: {row[0]}, Type: {row[1]}, Nullable: {row[2]}, Default: {row[3]}")
                        else:
                            print("  No results returned")
                    elif statement.upper().startswith('COMMENT'):
                        # Handle comments
                        print(f"Adding comment {i+1}...")
                        conn.execute(text(statement))
                    else:
                        # Handle DDL statements
                        print(f"Executing statement {i+1}: {statement[:50]}...")
                        result = conn.execute(text(statement))
                        print(f"  Statement executed successfully")
                
                print("Transaction committed successfully!")
        
        print("\n✅ Migration completed successfully!")
        print("\nRollover configuration columns added:")
        print("  - rollover_unused (BOOLEAN, DEFAULT FALSE)")
        print("  - rollover_overspend (BOOLEAN, DEFAULT FALSE)")  
        print("  - rollover_amount (REAL, DEFAULT 0.0)")
        
        return True
        
    except SQLAlchemyError as e:
        print(f"\n❌ Database error during migration:")
        print(f"Error: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error during migration:")
        print(f"Error: {str(e)}")
        return False

def verify_migration():
    """Verify that the migration was applied correctly"""
    
    print("\nVerifying migration...")
    
    try:
        engine = create_engine(DATABASE_URL)
        
        verification_sql = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'category_budgets' 
        AND column_name IN ('rollover_unused', 'rollover_overspend', 'rollover_amount')
        ORDER BY column_name;
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(verification_sql))
            columns = result.fetchall()
            
            if len(columns) == 3:
                print("✅ All rollover columns found:")
                for col in columns:
                    print(f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
                return True
            else:
                print(f"❌ Expected 3 columns, found {len(columns)}")
                return False
                
    except Exception as e:
        print(f"❌ Error verifying migration: {e}")
        return False

if __name__ == "__main__":
    print("PostgreSQL Rollover Configuration Migration")
    print("=" * 50)
    
    if not DATABASE_URL or "postgresql" not in DATABASE_URL:
        print("❌ Error: DATABASE_URL not set or not a PostgreSQL URL")
        print("Please set your DATABASE_URL environment variable or update the script")
        sys.exit(1)
    
    # Run migration
    success = run_migration()
    
    if success:
        # Verify migration
        verify_migration()
        print("\n🎉 Migration process completed!")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)