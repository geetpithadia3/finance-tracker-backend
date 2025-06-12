# Finance Tracker API (Python)

A comprehensive, modular finance tracking application built with FastAPI, featuring advanced budgeting, recurring transactions, and smart allocation systems.

## Quick Start

### SQLite (Default - No setup required)

```bash
cd finance-tracker-python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy SQLite environment configuration
cp .env.sqlite .env

# Run the application
uvicorn app.main:app --reload
# Or: python -m app.main
```

### PostgreSQL (Production)

```bash
cd finance-tracker-python

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install PostgreSQL dependencies
pip install -r requirements-postgres.txt

# Set up PostgreSQL database (see Database Configuration section)
# Then copy PostgreSQL environment configuration
cp .env.postgresql .env
# Edit .env with your database credentials

# Run the application
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000` with automatic documentation at `/docs`.

## Architecture

Modular, scalable structure following domain-driven design principles:

```
app/
├── routers/
│   ├── __init__.py
│   ├── auth.py                    # Authentication endpoints
│   ├── categories.py              # Category management
│   ├── transactions.py            # Transaction CRUD operations
│   ├── budgets.py                 # Budget management & reporting
│   ├── dashboard.py               # Dashboard analytics
│   ├── recurring_transactions.py  # Recurring transaction management
│   ├── expenses.py                # Expense filtering & analysis
│   └── allocation.py              # Smart allocation system
├── services/
│   ├── __init__.py
│   ├── date_service.py            # Date calculation utilities
│   └── budget_service.py          # Budget business logic
├── main.py                        # FastAPI app setup & router registration
├── models.py                      # SQLAlchemy database models
├── schemas.py                     # Pydantic request/response models
├── auth.py                        # JWT authentication utilities
├── database.py                    # Database configuration
└── config.py                      # Application settings
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user (with optional category seeding)
- `POST /auth/login` - Login user and get JWT token

### Categories
- `POST /categories` - Create category
- `GET /categories` - List user categories
- `PUT /categories/{id}` - Update category
- `POST /categories/seed` - Seed default categories for current user
- `POST /categories/seed/custom` - Create custom categories from list
- `GET /categories/defaults` - Get default category templates

### Transactions
- `POST /transactions` - Create single or bulk transactions
- `GET /transactions` - List user transactions
- `PUT /transactions` - Update single or bulk transactions
- `PUT /transactions/{id}` - Update specific transaction
- `POST /transactions/list` - List transactions by month

### Budgets
- `POST /budgets` - Create budget with category limits
- `GET /budgets` - Get budget details for period
- `GET /budgets/comparison/monthly` - Monthly budget comparison
- `GET /budgets/report` - Download budget report (CSV/JSON)
- `GET /budgets/categories` - Get categories for budgeting

### Dashboard
- `GET /dashboard` - Get financial overview for period
- `GET /dashboard/expenses-by-category` - Expenses grouped by category

### Recurring Transactions
- `POST /recurring-transactions` - Create recurring transaction
- `GET /recurring-transactions` - List active recurring transactions
- `GET /recurring-transactions/{id}` - Get specific recurring transaction
- `PUT /recurring-transactions/{id}` - Update recurring transaction
- `PUT /recurring-transactions/{id}/status` - Update status (active/inactive)
- `DELETE /recurring-transactions/{id}` - Delete recurring transaction

### Expenses
- `GET /expenses` - List expenses by month
- `POST /expenses/list` - List expenses by month (POST request)

### Smart Allocation
- `GET /allocation` - Get smart allocation recommendations

### Health & Monitoring
- `GET /` - API information
- `GET /health` - Comprehensive health check with database connectivity
- `GET /health/database` - Detailed database information and status
- `GET /tutorial` - Tutorial/documentation page

## Features

### Core Features
- ✅ **Modular Architecture**: Domain-separated routers and services
- ✅ **JWT Authentication**: Secure user authentication
- ✅ **Multi-database Support**: SQLite (development) and PostgreSQL (production)
- ✅ **Configuration Profiles**: Easy database switching via `DATABASE_PROFILE` environment variable
- ✅ **Database Health Monitoring**: Built-in connectivity checks and status endpoints
- ✅ **CORS Support**: Cross-origin resource sharing
- ✅ **Input Validation**: Comprehensive validation with Pydantic
- ✅ **Auto Documentation**: Interactive API docs at `/docs`

### Advanced Features
- ✅ **Category-based Budgeting**: Set limits per category with spending tracking
- ✅ **Auto-seeded Categories**: 19 pre-defined categories for new users (optional)
- ✅ **Recurring Transactions**: Flexible scheduling with date flexibility options
- ✅ **Smart Allocation**: AI-powered budget allocation recommendations
- ✅ **Bulk Operations**: Create/update multiple transactions at once
- ✅ **Expense Analytics**: Category-based expense analysis
- ✅ **Report Generation**: CSV export for budget reports
- ✅ **Dashboard Analytics**: Real-time financial overview

### Business Logic Features
- ✅ **Budget Status Tracking**: Over budget, near limit, under budget alerts
- ✅ **Date Flexibility**: Recurring transactions with smart date handling
- ✅ **Transaction Priorities**: Critical, high, medium, low priority levels
- ✅ **Variable Amount Support**: Handle transactions with estimated ranges

## Database Configuration

The application supports both SQLite and PostgreSQL databases through configuration profiles, allowing seamless switching between development and production environments.

### 🔧 Configuration Profiles

Switch databases using the `DATABASE_PROFILE` environment variable:
- `sqlite` - File-based database (default, zero setup)
- `postgresql` - Production-ready database server

### 📦 SQLite (Default - Development)

**Perfect for:** Development, testing, small deployments, quick prototyping

**Features:**
- Zero setup required
- File-based storage
- Built-in with Python
- Automatic table creation

```bash
# Quick start with SQLite
cp .env.sqlite .env
pip install -r requirements.txt
uvicorn app.main:app --reload

# Or manually configure:
echo "DATABASE_PROFILE=sqlite" > .env
echo "SQLITE_DATABASE_URL=sqlite:///./finance_tracker.db" >> .env
echo "SECRET_KEY=your-secret-key-here" >> .env
```

### 🐘 PostgreSQL (Production)

**Perfect for:** Production deployments, high concurrency, data integrity, scalability

**Features:**
- Production-grade performance
- ACID compliance
- Advanced querying capabilities
- Connection pooling and optimization

```bash
# Setup for PostgreSQL
pip install -r requirements-postgres.txt
cp .env.postgresql .env

# Edit .env with your PostgreSQL credentials:
DATABASE_PROFILE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=finance_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DATABASE=finance_tracker
SECRET_KEY=your-secret-key-here
DEBUG=false
```

### 🚀 Quick Database Switching

Switch between databases instantly:

```bash
# Development with SQLite
export DATABASE_PROFILE=sqlite
uvicorn app.main:app --reload

# Production with PostgreSQL  
export DATABASE_PROFILE=postgresql
uvicorn app.main:app --reload

# Check current database status
curl http://localhost:8000/health/database
```

### 🛠️ PostgreSQL Server Setup

#### 1. Install PostgreSQL

```bash
# macOS with Homebrew
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/

# Docker (Quick setup)
docker run --name finance-postgres \
  -e POSTGRES_USER=finance_user \
  -e POSTGRES_PASSWORD=finance_password \
  -e POSTGRES_DB=finance_tracker \
  -p 5432:5432 \
  -d postgres:15
```

#### 2. Create Database and User

```sql
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE finance_tracker;
CREATE USER finance_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE finance_tracker TO finance_user;

# Grant schema permissions (PostgreSQL 15+)
\c finance_tracker
GRANT ALL ON SCHEMA public TO finance_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO finance_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO finance_user;

\q
```

#### 3. Test Connection

```bash
# Test connection
psql -h localhost -U finance_user -d finance_tracker

# Or test with the app
curl http://localhost:8000/health/database
```

### 🔍 Health Monitoring

Monitor your database connection status:

```bash
# Check overall health
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "timestamp": "2024-06-11T21:27:39.409Z",
  "service": "Finance Tracker API",
  "version": "1.0.0",
  "database": {
    "profile": "postgresql",
    "connection": "connected",
    "url_masked": "postgresql://finance_user:****@localhost:5432/finance_tracker"
  }
}

# Detailed database info
curl http://localhost:8000/health/database

# Response:
{
  "profile": "postgresql",
  "is_sqlite": false,
  "is_postgresql": true,
  "connection_status": "connected",
  "url_masked": "postgresql://finance_user:****@localhost:5432/finance_tracker"
}
```

### ⚙️ Environment Configuration

Complete environment variable reference:

```env
# Application Settings
APP_NAME=Finance Tracker API
VERSION=1.0.0
DEBUG=true

# Database Configuration
DATABASE_PROFILE=sqlite  # or postgresql

# SQLite Configuration (when DATABASE_PROFILE=sqlite)
SQLITE_DATABASE_URL=sqlite:///./finance_tracker.db

# PostgreSQL Configuration (when DATABASE_PROFILE=postgresql)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=finance_user
POSTGRES_PASSWORD=finance_password
POSTGRES_DATABASE=finance_tracker

# Alternative: Direct PostgreSQL URL
# POSTGRESQL_DATABASE_URL=postgresql://finance_user:finance_password@localhost:5432/finance_tracker

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=["*"]
```

### 📋 Database Comparison

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| **Setup** | Zero configuration | Requires server setup |
| **Performance** | Good for < 100k records | Excellent for millions of records |
| **Concurrency** | Limited concurrent writes | High concurrent read/write |
| **ACID Compliance** | Yes | Yes |
| **Backup** | Copy file | pg_dump/pg_restore |
| **Deployment** | Single file | Database server |
| **Use Case** | Development, small apps | Production, enterprise |
| **Memory Usage** | Minimal | Configurable |
| **Connection Pooling** | File-based | Built-in advanced pooling |

### 🔄 Migration Between Databases

```bash
# Export data from SQLite
# (Manual process - export via API or direct SQL)

# Import to PostgreSQL
# 1. Set up PostgreSQL database
# 2. Change DATABASE_PROFILE=postgresql
# 3. Run application (auto-creates tables)
# 4. Import data via API or SQL scripts
```

## Extending the Application

The modular architecture makes it easy to extend:

1. **Add new domain**: Create new router in `app/routers/`
2. **Add business logic**: Create service in `app/services/`
3. **Add models**: Define in `models.py`
4. **Add validation**: Define schemas in `schemas.py`
5. **Register router**: Add to `main.py` router includes

### Example: Adding a new feature

```python
# 1. Create app/routers/investments.py
from fastapi import APIRouter
router = APIRouter(prefix="/investments", tags=["investments"])

@router.get("")
def list_investments():
    return {"message": "Investment feature"}

# 2. Add to app/main.py
from app.routers import investments
app.include_router(investments.router)
```

## Example Usage

```bash
# Register (with default categories)
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "secret"}'

# Register without default categories
curl -X POST "http://localhost:8000/auth/register?seed_categories=false" \
  -H "Content-Type: application/json" \
  -d '{"username": "jane", "password": "secret"}'

# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "secret"}'

# Create category (with token)
curl -X POST "http://localhost:8000/categories" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Food"}'

# Create transaction
curl -X POST "http://localhost:8000/transactions" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "EXPENSE", "amount": 25.50, "description": "Lunch", "category_id": "CATEGORY_ID", "occurred_on": "2024-06-11T12:00:00"}'

# Create budget
curl -X POST "http://localhost:8000/budgets" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"year_month": "2024-06", "category_limits": [{"category_id": "CATEGORY_ID", "budget_amount": 500.00}]}'

# Get dashboard
curl -X GET "http://localhost:8000/dashboard?year_month=2024-06" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get default category templates
curl -X GET "http://localhost:8000/categories/defaults"

# Seed default categories for existing user
curl -X POST "http://localhost:8000/categories/seed" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create custom categories
curl -X POST "http://localhost:8000/categories/seed/custom" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '["Cryptocurrency", "Pet Expenses", "Home Improvement"]'
```

## Development

### Project Structure Benefits

- **Scalability**: Easy to add new features without touching existing code
- **Maintainability**: Clear separation of concerns
- **Testing**: Each router/service can be tested independently  
- **Team Development**: Multiple developers can work on different domains
- **Code Reuse**: Services can be shared across routers
- **Database Flexibility**: Switch between SQLite and PostgreSQL without code changes
- **Environment Parity**: Same codebase runs in development (SQLite) and production (PostgreSQL)