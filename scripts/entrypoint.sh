#!/bin/bash
set -e

if [ "${DATABASE_PROFILE:-sqlite}" = "postgresql" ]; then
  echo "Running Migrations..."
  python -m alembic upgrade head
fi

# Start App
echo "Starting Uvicorn..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
