# Render Deployment Guide

## Backend Service Setup

### 1. Environment Variables (Set in Render Dashboard)

**🔑 Security Variables (CRITICAL):**
```bash
SECRET_KEY=generate-your-own-secure-key-using-command-below
DEBUG=False
```

**Generate your own secret key:**
```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

**🗄️ Database Variables:**
```bash
DATABASE_PROFILE=postgresql
# These will be auto-populated if you connect a Render PostgreSQL database
POSTGRES_HOST=dpg-xxxxx-a.oregon-postgres.render.com
POSTGRES_PORT=5432
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DATABASE=your_db_name
```

**🌐 CORS Variables:**
```bash
# Update this with your actual frontend URL
ALLOWED_ORIGINS=https://your-frontend-app.onrender.com,http://localhost:3000,http://localhost:5173
```

**⚡ Performance Variables:**
```bash
PYTHONUNBUFFERED=1
PORT=10000
```

### 2. Render Service Configuration

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Environment:** `Python 3`

### 3. Database Setup Options

**Option A: Render PostgreSQL (Recommended)**
1. Create a PostgreSQL database in Render
2. Connect it to your web service
3. Environment variables will be auto-populated

**Option B: External Database**
1. Set `DATABASE_URL` environment variable:
```bash
DATABASE_URL=postgresql://user:password@host:port/database
```

### 4. Security Checklist

- [ ] Generated new SECRET_KEY (never use the example one in production)
- [ ] Set DEBUG=False
- [ ] Configured database with secure credentials
- [ ] Updated ALLOWED_ORIGINS with your frontend URL
- [ ] Removed any .env files from repository
- [ ] Database credentials not in code

## Frontend Service Setup

### Environment Variables for Frontend:
```bash
VITE_API_BASE_URL=https://your-backend-app.onrender.com
```

### Build Settings:
**Build Command:**
```bash
npm install && npm run build
```

**Publish Directory:** `dist`

## Post-Deployment Steps

1. **Test the API:** Visit `https://your-backend-app.onrender.com/docs`
2. **Test authentication:** Try logging in from frontend
3. **Check logs:** Monitor Render logs for any errors
4. **Database migration:** Ensure tables are created properly

## Troubleshooting

**Common Issues:**

1. **CORS errors:** Check ALLOWED_ORIGINS includes your frontend URL
2. **Database connection fails:** Verify PostgreSQL environment variables
3. **Secret key errors:** Ensure SECRET_KEY is set and not the default
4. **Port binding issues:** Ensure PORT=10000 is set

**Debug Commands:**
```bash
# Check environment variables (in Render shell)
env | grep -E "(SECRET_KEY|DATABASE|POSTGRES|DEBUG)"

# Test database connection
python -c "from app.database import engine; print('DB connection OK')"
```

## Security Notes

- Never commit environment files (.env) to git
- Regularly rotate your SECRET_KEY
- Use Render's managed PostgreSQL for production
- Monitor application logs for suspicious activity
- Keep dependencies updated

## Getting Your URLs

After deployment:
- Backend: `https://your-backend-service-name.onrender.com`
- Frontend: `https://your-frontend-service-name.onrender.com`

Update the ALLOWED_ORIGINS and VITE_API_BASE_URL with these actual URLs.