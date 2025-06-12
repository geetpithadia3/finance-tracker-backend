#!/usr/bin/env python3
"""
🔧 Interactive Supabase URL Helper
Help fix your Supabase connection by guiding you through getting the correct URL
"""

import re
from urllib.parse import quote_plus

def url_encode_password(password):
    """URL encode special characters in password"""
    return quote_plus(password)

def validate_supabase_url(url):
    """Validate Supabase URL format"""
    pattern = r'postgresql://postgres:(.+)@db\.([a-z0-9]+)\.supabase\.co:5432/postgres'
    return re.match(pattern, url) is not None

def main():
    print("🚀 Supabase Connection URL Helper")
    print("=" * 50)
    print("This tool will help you create the correct Supabase connection URL")
    print()
    
    print("📋 First, get your connection details from Supabase:")
    print("1. Go to https://supabase.com/dashboard")
    print("2. Select your project")
    print("3. Go to Settings → Database")
    print("4. Find 'Connection info' section")
    print()
    
    # Get project details
    project_id = input("🔹 Enter your Project Reference ID (e.g., 'abcd1234efgh5678'): ").strip()
    if not project_id:
        print("❌ Project ID is required")
        return
    
    password = input("🔹 Enter your database password: ").strip()
    if not password:
        print("❌ Password is required")
        return
    
    # Check for special characters
    special_chars = ['@', '#', '$', '%', '&', '+', '=', '?', ' ']
    has_special = any(char in password for char in special_chars)
    
    if has_special:
        print(f"⚠️  Password contains special characters: {[c for c in special_chars if c in password]}")
        encoded_password = url_encode_password(password)
        print(f"🔧 URL-encoded password: {encoded_password}")
    else:
        encoded_password = password
        print("✅ Password doesn't need URL encoding")
    
    # Generate URLs
    hostname = f"db.{project_id}.supabase.co"
    connection_url = f"postgresql://postgres:{encoded_password}@{hostname}:5432/postgres"
    
    print("\n" + "=" * 50)
    print("🎯 Your Connection Details:")
    print("=" * 50)
    print(f"Host: {hostname}")
    print(f"Database: postgres")
    print(f"Port: 5432")
    print(f"User: postgres")
    print(f"Password: {password}")
    print(f"Encoded Password: {encoded_password}")
    print()
    print("🔗 Connection URL:")
    print(connection_url)
    print()
    
    # Generate .env content
    print("📝 Add this to your .env file:")
    print("-" * 30)
    print("DATABASE_PROFILE=postgresql")
    print(f"POSTGRESQL_DATABASE_URL={connection_url}")
    print()
    print("# Alternative: Individual components")
    print(f"# POSTGRES_HOST={hostname}")
    print("# POSTGRES_PORT=5432")
    print("# POSTGRES_USER=postgres")
    print(f"# POSTGRES_PASSWORD={password}")
    print("# POSTGRES_DATABASE=postgres")
    print("-" * 30)
    
    # Test DNS
    print("\n🔍 Testing hostname resolution...")
    import subprocess
    try:
        result = subprocess.run(['nslookup', hostname], 
                              capture_output=True, text=True, timeout=10)
        if "can't find" in result.stdout.lower() or "no answer" in result.stdout.lower():
            print("❌ Hostname cannot be resolved!")
            print("💡 Possible issues:")
            print("   - Project ID is incorrect")
            print("   - Project is paused/deleted")
            print("   - Project not fully initialized")
            print("   - Network connectivity issues")
        else:
            print("✅ Hostname resolves successfully!")
    except Exception as e:
        print(f"⚠️  Could not test hostname: {e}")
    
    print("\n🧪 Next Steps:")
    print("1. Update your .env file with the connection URL above")
    print("2. Run: python test-supabase-connection.py")
    print("3. If successful, run: ./start-with-supabase.sh")
    
if __name__ == "__main__":
    main()