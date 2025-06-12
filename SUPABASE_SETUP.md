# 🚀 Supabase PostgreSQL Setup Guide

This guide shows how to set up the Finance Tracker Python app with Supabase PostgreSQL database.

## 📋 Prerequisites

- Supabase account (free tier available)
- Python finance tracker app
- PostgreSQL dependencies installed

## 🔧 Step 1: Create Supabase Project

1. **Sign up/Login to Supabase**
   - Go to https://supabase.com
   - Create account or log in
   - Click "New Project"

2. **Create New Project**
   - Choose organization
   - Enter project name: `finance-tracker`
   - Enter database password (save this!)
   - Select region (choose closest to your users)
   - Click "Create new project"

3. **Wait for Setup**
   - Project setup takes 1-2 minutes
   - You'll see a dashboard when ready

## ⚠️ Important: Password URL Encoding

If your Supabase password contains special characters like `@`, `#`, `$`, `%`, etc., you must URL-encode them:

| Character | URL Encoded |
|-----------|-------------|
| `@`       | `%40`       |
| `#`       | `%23`       |
| `$`       | `%24`       |
| `%`       | `%25`       |
| `&`       | `%26`       |
| `+`       | `%2B`       |
| `=`       | `%3D`       |

**Example:** If password is `MyPass@123`, use `MyPass%40123` in the connection string.

## 🔑 Step 2: Get Database Connection Details

1. **Navigate to Settings**
   - Click "Settings" in left sidebar
   - Click "Database"

2. **Copy Connection Details**
   ```
   Host: db.xxx.supabase.co
   Database name: postgres
   Port: 5432
   User: postgres
   Password: [your-password]
   ```

3. **Get Connection URI**
   - Look for "Connection string" section
   - Copy the PostgreSQL URI format:
   ```
   postgresql://postgres:[password]@db.xxx.supabase.co:5432/postgres
   ```

## ⚙️ Step 3: Configure Environment

1. **Install PostgreSQL Dependencies**
   ```bash
   cd finance-tracker-python
   source venv/bin/activate
   pip install -r requirements-postgres.txt
   ```

2. **Create Environment File**
   ```bash
   cp .env.postgresql .env
   ```

3. **Update .env with Supabase Credentials**
   ```env
   # Application Settings
   APP_NAME=Finance Tracker API
   VERSION=1.0.0
   DEBUG=true

   # Database Configuration
   DATABASE_PROFILE=postgresql

   # Supabase PostgreSQL Configuration
   POSTGRESQL_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxx.supabase.co:5432/postgres

   # Alternative: Individual components
   # POSTGRES_HOST=db.xxx.supabase.co
   # POSTGRES_PORT=5432
   # POSTGRES_USER=postgres
   # POSTGRES_PASSWORD=YOUR_PASSWORD
   # POSTGRES_DATABASE=postgres

   # Security
   SECRET_KEY=your-secret-key-change-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30

   # CORS
   ALLOWED_ORIGINS=["*"]
   ```

   **⚠️ Important:** Replace `YOUR_PASSWORD` and `xxx` with your actual Supabase credentials!

## 🚀 Step 4: Start the Application

1. **Test Database Connection**
   ```bash
   curl http://localhost:8000/health/database
   ```

2. **Start the App**
   ```bash
   uvicorn app.main:app --reload
   ```

3. **Verify Connection**
   ```bash
   # Check health endpoint
   curl http://localhost:8000/health

   # Expected response:
   {
     "status": "healthy",
     "database": {
       "profile": "postgresql",
       "connection": "connected",
       "url_masked": "postgresql://postgres:****@db.xxx.supabase.co:5432/postgres"
     }
   }
   ```

## 📊 Step 5: Verify Tables in Supabase

1. **Open Supabase Dashboard**
   - Go to your project dashboard
   - Click "Table Editor" in sidebar

2. **Check Created Tables**
   After starting the app, you should see these tables:
   - `users`
   - `categories` 
   - `transactions`
   - `budgets`
   - `category_budgets`
   - `recurring_transactions`

## 🧪 Step 6: Test the API

1. **Register a User**
   ```bash
   curl -X POST "http://localhost:8000/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "testpass123"}'
   ```

2. **Login**
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "testpass123"}'
   ```

3. **Check Categories (should show 19 default categories)**
   ```bash
   curl -X GET "http://localhost:8000/categories" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

## 🔒 Step 7: Security Configuration

1. **Enable Row Level Security (RLS)**
   - In Supabase dashboard, go to "Authentication" > "Policies"
   - Enable RLS for production use
   - Create policies for your tables

2. **Update CORS for Production**
   ```env
   # Replace * with your frontend domain
   ALLOWED_ORIGINS=["https://your-frontend-domain.com"]
   ```

3. **Use Strong Secret Key**
   ```bash
   # Generate secure secret key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

## 🔧 Troubleshooting

### Connection Issues

1. **Check Supabase Project Status**
   - Ensure project is active (green status)
   - Verify no pausing due to inactivity

2. **Verify Credentials**
   ```bash
   # Test connection with psql
   psql "postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres"
   ```

3. **Check Network**
   - Ensure your IP isn't blocked
   - Try from different network if needed

### Common Errors

1. **"could not connect to server"**
   - Check internet connection
   - Verify Supabase URL and credentials
   - Check if project is paused

2. **"authentication failed"**
   - Double-check password
   - Ensure no special characters are URL-encoded

3. **"database does not exist"**
   - Use `postgres` as database name (default)
   - Don't create custom database name

## 🎯 Production Considerations

1. **Environment Variables**
   - Use environment variables or secrets management
   - Never commit credentials to version control

2. **Connection Pooling**
   - Supabase handles connection pooling automatically
   - Monitor connection usage in dashboard

3. **Backups**
   - Supabase provides automatic backups
   - Consider additional backup strategy for critical data

4. **Monitoring**
   - Use Supabase dashboard for monitoring
   - Set up alerts for database issues

## 📚 Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Connection Strings](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING)
- [FastAPI with PostgreSQL](https://fastapi.tiangolo.com/tutorial/sql-databases/)

## 🆘 Need Help?

1. Check Supabase community: https://github.com/supabase/supabase/discussions
2. Review app logs for detailed error messages
3. Use `/health/database` endpoint to diagnose connection issues