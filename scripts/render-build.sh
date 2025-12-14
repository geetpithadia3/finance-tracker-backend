#!/usr/bin/env bash
# Render build script for Finance Tracker V2

set -e  # Exit on error

echo "🚀 Starting Render build process..."

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations
echo "🗄️  Running database migrations..."
alembic upgrade head

echo "✅ Build completed successfully!"
