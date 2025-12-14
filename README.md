# Finance Tracker V2

**"Financial Clarity, Without the Math Anxiety."**

A personal finance tracker built on double-entry accounting principles. Professional-grade accuracy wrapped in a simple API.

## What Makes This Different

Unlike typical expense trackers that just log transactions, this system:
- **Maintains accounting integrity** - Every transaction is balanced (debits = credits)
- **Tracks real money movement** - See exactly where your money comes from and goes to
- **Handles complex scenarios** - Split transactions, shared expenses, multiple payment methods
- **Auto-categorizes** - Smart pattern matching to categorize transactions automatically
- **Imports bulk data** - CSV import for bank statements

## Quick Start

### Local Development (SQLite)

```bash
# Clone and navigate to the project
cd finance-tracker-python

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.sqlite .env

# Run migrations
alembic upgrade head

# Start the application
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000` with interactive documentation at `/docs`.

### Docker (Recommended for Production)

```bash
# Start with Docker Compose
docker-compose up --build

# The API will be available at http://localhost:8000
```

### PostgreSQL (Production)

For production deployments, configure PostgreSQL:

```bash
# Copy PostgreSQL environment template
cp .env.postgresql .env

# Edit .env with your database credentials
# DATABASE_PROFILE=postgresql
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_USER=finance_user
# POSTGRES_PASSWORD=your_secure_password
# POSTGRES_DATABASE=finance_tracker

# Run migrations
alembic upgrade head

# Start the application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Core Features

### 1. **Double-Entry Accounting**
Every transaction creates balanced ledger entries:
```
Purchase: Groceries $50
  Debit:  Groceries (Expense) +$50
  Credit: Cash (Asset)         -$50
```

### 2. **Split Transactions**
Break one purchase across multiple categories:
```json
{
  "description": "Target Run",
  "amount": 150.00,
  "splits": [
    {"category_id": "groceries-uuid", "amount": 100.00},
    {"category_id": "clothing-uuid", "amount": 50.00}
  ]
}
```

### 3. **Personal Share Tracking**
Track shared expenses and who owes what:
```json
{
  "description": "Team Dinner",
  "amount": 200.00,
  "share": {
    "method": "FIXED",
    "value": 80.00
  }
}
```
Result: $80 expense, $120 reimbursable

### 4. **Multiple Payment Sources**
Specify which account you used:
- Credit cards
- Cash
- Checking account
- Savings account

### 5. **CSV Import**
Drag and drop bank statements for bulk import with intelligent auto-categorization.

### 6. **Auto-Categorization**
Create rules to automatically categorize transactions:
```
"Uber" → Transport
"Whole Foods" → Groceries
"Netflix" → Entertainment
```

## Architecture

```
app/
├── core/                     # Infrastructure (auth, logging, middleware)
├── routers/                  # API endpoints
│   ├── auth.py
│   ├── transactions.py
│   ├── categories.py
│   ├── accounts.py
│   ├── imports.py
│   ├── mappings.py
│   └── reports.py
├── services/                 # Business logic
│   ├── ledger_service.py     # Core double-entry logic
│   ├── transaction_service.py
│   ├── import_service.py
│   └── mapping_service.py
├── repositories/             # Data access layer
├── models.py                 # Database models
└── schemas.py                # Request/response schemas
```

### Design Principles
- **Layered Architecture**: Presentation → Service → Repository → Database
- **Domain-Driven Design**: Clear separation of concerns
- **Double-Entry Ledger**: Every transaction is balanced
- **Type Safety**: Pydantic validation on all inputs
- **Database Agnostic**: SQLite (dev) or PostgreSQL (prod)

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create new user account
- `POST /api/auth/login` - Login and get JWT token

### Categories (Expense Accounts)
- `GET /api/categories` - List all categories
- `POST /api/categories` - Create new category
- `PUT /api/categories/{id}` - Update category
- `DELETE /api/categories/{id}` - Delete category

### Accounts (Assets & Liabilities)
- `GET /api/accounts` - List all accounts
- `POST /api/accounts` - Create new account (Cash, Credit Card, etc.)

### Transactions
- `POST /api/transactions` - Create transaction (supports splits & shares)
- `GET /api/transactions` - List transactions with filters
- `PUT /api/transactions/{id}` - Update transaction
- `DELETE /api/transactions/{id}` - Delete transaction

### Imports
- `POST /api/imports/csv` - Bulk import from CSV

### Mapping Rules
- `GET /api/mappings` - List auto-categorization rules
- `POST /api/mappings` - Create new rule
- `DELETE /api/mappings/{id}` - Delete rule

### Reports
- `GET /api/reports/spending` - Spending analysis by category
- `GET /api/reports/balance-sheet` - Account balances

## Example Usage

### 1. Register and Login
```bash
# Register
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "secret123"}'

# Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "john", "password": "secret123"}'
```

### 2. Create a Simple Transaction
```bash
curl -X POST "http://localhost:8000/api/transactions" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": "groceries-category-id",
    "type": "DEBIT",
    "description": "Whole Foods",
    "amount": 85.50,
    "occurred_on": "2024-12-14T12:00:00"
  }'
```

### 3. Split Transaction
```bash
curl -X POST "http://localhost:8000/api/transactions" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": "groceries-category-id",
    "type": "DEBIT",
    "description": "Target Run",
    "amount": 150.00,
    "occurred_on": "2024-12-14T14:00:00",
    "splits": [
      {"category_id": "groceries-id", "amount": 100.00, "description": "Food"},
      {"category_id": "clothing-id", "amount": 50.00, "description": "Shirt"}
    ]
  }'
```

### 4. Import CSV
```bash
curl -X POST "http://localhost:8000/api/imports/csv" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@statement.csv"
```

## Database Schema

The application uses a double-entry ledger model:

### Core Tables
- **parties** - Economic actors (users, households)
- **accounts** - Asset, Liability, Income, and Expense accounts
- **ledger_transactions** - Transaction headers (date, description)
- **entries** - Individual debits and credits

### Supporting Tables
- **users** - Authentication credentials
- **mapping_rules** - Auto-categorization rules
- **budget_rules** - Spending limits (future)
- **recurring_templates** - Recurring transactions (future)

## Configuration

### Environment Variables

```env
# Application
APP_NAME=Finance Tracker V2
VERSION=2.0.0
DEBUG=true

# Database
DATABASE_PROFILE=sqlite  # or postgresql
SQLITE_DATABASE_URL=sqlite:///./finance_tracker.db

# PostgreSQL (when DATABASE_PROFILE=postgresql)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=finance_user
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=finance_tracker

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
ALLOWED_ORIGINS=["http://localhost:3000"]
```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_transfers_splits.py
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Code Quality
```bash
# Format code
black app/ tests/

# Lint
flake8 app/ tests/

# Type checking
mypy app/
```

## Documentation

See the `/docs` directory for detailed documentation:
- [Architecture](docs/architecture.md) - System design and patterns
- [Technical Specification](docs/technical_specification.md) - Database and API design
- [Transaction API V2](docs/transaction_api_v2.md) - Transaction endpoint details
- [Vision](docs/vision.md) - Product philosophy and goals
- [Roadmap](docs/roadmap.md) - Implementation progress

## Deployment

### Docker
```bash
docker build -t finance-tracker-v2 .
docker run -p 8000:8000 --env-file .env finance-tracker-v2
```

### Docker Compose
```bash
docker-compose up -d
```

### Render.com
A `render.yaml` is included for one-click deployment to Render.

## Tech Stack

- **Framework**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Migrations**: Alembic
- **Validation**: Pydantic v2
- **Authentication**: JWT (python-jose)
- **Testing**: pytest
- **Python**: 3.11+

## License

MIT

## Support

For issues and questions, please open an issue on GitHub.

---

**Version**: 2.0.0
**Status**: Production Ready
