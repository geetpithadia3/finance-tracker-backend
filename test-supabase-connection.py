#!/usr/bin/env python3
"""
🔌 Supabase Connection Test Script
Test your Supabase PostgreSQL connection before starting the app
"""

import os
import sys
from urllib.parse import quote_plus

def url_encode_password(password):
    """URL encode special characters in password"""
    return quote_plus(password)

def test_connection():
    """Test Supabase connection with current configuration"""
    try:
        from app.config import settings
        from app.database import check_database_connection, get_database_info
        
        print("🔧 Supabase Connection Test")
        print("=" * 50)
        
        # Show current configuration
        print(f"Database Profile: {settings.database_profile}")
        print(f"Is PostgreSQL: {settings.is_postgresql}")
        
        if not settings.is_postgresql:
            print("❌ Database profile is not set to PostgreSQL")
            print("💡 Make sure DATABASE_PROFILE=postgresql in your .env file")
            return False
        
        db_info = get_database_info()
        print(f"Connection URL: {db_info['url']}")
        print()
        
        # Test connection
        print("🔌 Testing connection...")
        if check_database_connection():
            print("✅ SUCCESS: Supabase connection working!")
            print("🚀 You can now start the application")
            return True
        else:
            print("❌ FAILED: Could not connect to Supabase")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're in the right directory and virtual environment is activated")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def show_troubleshooting():
    """Show troubleshooting tips"""
    print("\n🔧 Troubleshooting Tips:")
    print("=" * 50)
    print("1. Check your Supabase project status at https://supabase.com/dashboard")
    print("2. Verify your database password and URL")
    print("3. Ensure special characters in password are URL-encoded:")
    print("   @ → %40, # → %23, $ → %24, % → %25")
    print("4. Check your internet connection")
    print("5. Try accessing Supabase dashboard to verify project is active")
    print("\n📝 Example .env configuration:")
    print("DATABASE_PROFILE=postgresql")
    print("POSTGRESQL_DATABASE_URL=postgresql://postgres:your_password@db.xxx.supabase.co:5432/postgres")

def main():
    """Main function"""
    print("🚀 Finance Tracker - Supabase Connection Test")
    print("=" * 60)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        print("💡 Copy .env.postgresql to .env and configure your Supabase credentials")
        return
    
    # Test connection
    if not test_connection():
        show_troubleshooting()
        sys.exit(1)
    
    print("\n🎉 Connection test completed successfully!")
    print("Run: uvicorn app.main:app --reload")

if __name__ == "__main__":
    main()