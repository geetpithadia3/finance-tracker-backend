#!/bin/bash

# 🚀 Start Finance Tracker with Supabase PostgreSQL
# Usage: ./start-with-supabase.sh

echo "🔧 Setting up Finance Tracker with Supabase PostgreSQL..."

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Run 'python -m venv venv' first."
    exit 1
fi

# Install PostgreSQL dependencies
echo "📦 Installing PostgreSQL dependencies..."
pip install -r requirements-postgres.txt

# Copy PostgreSQL environment configuration
if [ -f ".env.postgresql" ]; then
    cp .env.postgresql .env
    echo "✅ PostgreSQL environment configuration loaded"
else
    echo "❌ .env.postgresql not found. Please configure Supabase credentials first."
    exit 1
fi

# Test database connection
echo "🔌 Testing Supabase connection..."
python -c "
from app.database import check_database_connection, get_database_info

db_info = get_database_info()
print(f'Database: {db_info[\"profile\"]} - {db_info[\"url\"]}')

if check_database_connection():
    print('✅ Supabase connection successful!')
else:
    print('❌ Supabase connection failed!')
    print('💡 Check your credentials in .env file')
    exit(1)
" || exit 1

echo "🚀 Starting Finance Tracker API with Supabase..."
echo "📊 Tables will be created automatically on first startup"
echo "🌐 API will be available at: http://localhost:8000"
echo "📚 API docs will be available at: http://localhost:8000/docs"
echo ""

# Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000