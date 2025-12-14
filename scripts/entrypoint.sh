#!/bin/bash
set -e

# Run migrations (only if using Postgres usually, but good practice to try)
# Using DATABASE_PROFILE from environment
echo "Running Migrations..."
alembic upgrade head

# Start App
echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
