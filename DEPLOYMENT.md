# Deployment Guide - Render.com

This guide will help you deploy Finance Tracker V2 to Render.com with a cloud PostgreSQL database.

## 📋 Prerequisites

Before deploying, you need:
1. A GitHub account with your code pushed
2. A Render account (free at [render.com](https://render.com))
3. **A cloud PostgreSQL database** (see options below)

## 🗄️ Database Setup (Do This First!)

Your app needs a PostgreSQL database. Choose one:

### Quick Option: Render PostgreSQL (Recommended)
- **Free tier**: 1 GB storage, 97 connections
- **Same platform**: Low latency, easy setup
- **Setup time**: 2 minutes

### Other Options:
- AWS RDS PostgreSQL
- Azure Database for PostgreSQL
- ElephantSQL
- Supabase
- Neon

📖 **See complete setup guide**: [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md)

**Important**: Get your database credentials ready before deploying:
- Host (e.g., `your-db.postgres.render.com`)
- Port (usually `5432`)
- Username
- Password
- Database name

---

## 🚀 Deploy to Render

### Option 1: Deploy from GitHub (Recommended)

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Deploy to Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click **New +** → **Blueprint**
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml` and configure everything

3. **Configure Database Credentials**

   After the service is created:
   - Go to your web service → **Environment** tab
   - Add these database variables (using your credentials from database setup):

   | Variable | Value |
   |----------|-------|
   | `POSTGRES_HOST` | Your database host |
   | `POSTGRES_PORT` | 5432 |
   | `POSTGRES_USER` | Your database username |
   | `POSTGRES_PASSWORD` | Your database password |
   | `POSTGRES_DATABASE` | Your database name |

   - Click **Save Changes**
   - Service will automatically redeploy

4. **Wait for Build**
   - Render will automatically:
     - Install dependencies
     - Run database migrations
     - Connect to your PostgreSQL database
     - Start the application
   - First build takes ~2-3 minutes

5. **Your API is Live!**
   - URL: `https://finance-tracker-v2.onrender.com`
   - API Docs: `https://finance-tracker-v2.onrender.com/docs`
   - Health Check: `https://finance-tracker-v2.onrender.com/health`

### Option 2: Manual Deploy

1. **Create New Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click **New +** → **Web Service**
   - Connect your GitHub repository

2. **Configure Service**
   ```
   Name: finance-tracker-v2
   Region: Oregon (US West)
   Branch: main
   Runtime: Python 3
   Build Command: bash scripts/render-build.sh
   Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   Plan: Free
   ```

3. **Set Environment Variables**

   Add these required variables:
   ```
   DATABASE_PROFILE=postgresql
   POSTGRES_HOST=<your-db-host>
   POSTGRES_PORT=5432
   POSTGRES_USER=<your-db-user>
   POSTGRES_PASSWORD=<your-db-password>
   POSTGRES_DATABASE=<your-db-name>
   SECRET_KEY=<auto-generate>
   DEBUG=false
   ALLOWED_ORIGINS=*
   ```

4. **Deploy**
   - Click **Create Web Service**
   - Wait for deployment to complete (~2-3 minutes)

## 🔧 Configuration

### Environment Variables

The following are configured via `render.yaml` and Render Dashboard:

#### Auto-Configured (via render.yaml)

| Variable | Value | Description |
|----------|-------|-------------|
| `PYTHON_VERSION` | 3.11.0 | Python runtime version |
| `DATABASE_PROFILE` | postgresql | Database type |
| `SECRET_KEY` | auto-generated | JWT secret key |
| `ALGORITHM` | HS256 | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Token expiration |
| `DEBUG` | false | Production mode |
| `ALLOWED_ORIGINS` | * | CORS origins (update for security) |

#### Manually Set (via Render Dashboard)

**Required - Add these in Render Dashboard → Environment:**

| Variable | Example Value | Description |
|----------|---------------|-------------|
| `POSTGRES_HOST` | `db.render.com` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_USER` | `finance_user` | Database username |
| `POSTGRES_PASSWORD` | `your-password` | Database password |
| `POSTGRES_DATABASE` | `finance_tracker` | Database name |

### Custom Domain (Optional)

1. Go to your service settings
2. Click **Custom Domains**
3. Add your domain: `api.yourdomain.com`
4. Update DNS with provided CNAME

## 📊 Database Configuration

This application **requires a PostgreSQL database**. Data persists across deployments and restarts.

### Recommended: Render PostgreSQL

**Benefits:**
- Same infrastructure as web service
- Free tier: 1 GB storage, 97 connections
- Automatic backups (paid plans)
- Low latency
- Easy setup

**Quick Setup:**
1. Render Dashboard → **New +** → **PostgreSQL**
2. Choose region: Oregon (same as web service)
3. Select plan: Free or Starter
4. Copy connection details
5. Add to web service environment variables

### Alternative: External PostgreSQL

Supported providers:
- **AWS RDS** - Enterprise-grade, scalable
- **Azure Database** - Microsoft ecosystem
- **ElephantSQL** - Simple managed PostgreSQL
- **Supabase** - Modern features, realtime
- **Neon** - Serverless, database branching

📖 **Complete setup guide**: [POSTGRESQL_SETUP.md](POSTGRESQL_SETUP.md)

## 🔒 Security Hardening

Before going to production, update these settings:

### 1. Update CORS Origins
Replace wildcard with your frontend domain:
```
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 2. Enable HTTPS Only
Render automatically provides HTTPS. Ensure your frontend uses:
```
https://finance-tracker-v2.onrender.com
```

### 3. Secret Key
Render auto-generates `SECRET_KEY`. To manually set:
```bash
# Generate secure key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to Render environment variables
```

## 🧪 Testing Your Deployment

### 1. Health Check
```bash
curl https://finance-tracker-v2.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-14T...",
  "service": "Finance Tracker V2",
  "version": "2.0.0"
}
```

### 2. API Documentation
Visit: `https://finance-tracker-v2.onrender.com/docs`

### 3. Create Test User
```bash
curl -X POST "https://finance-tracker-v2.onrender.com/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

## 🔄 Continuous Deployment

Render automatically redeploys when you push to `main`:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

Render will:
1. Pull latest code
2. Run build script
3. Run migrations
4. Restart service
5. Zero-downtime deployment

## 📈 Monitoring

### Logs
- View in Render Dashboard → Logs
- Real-time log streaming
- Filter by severity

### Metrics
Render provides:
- CPU usage
- Memory usage
- Request count
- Response times

### Alerts
Set up in Render Dashboard:
- Email notifications
- Slack integration
- Webhook alerts

## 🐛 Troubleshooting

### Build Fails

**Error: `requirements.txt not found`**
```bash
# Ensure file exists at root
ls requirements.txt

# Check git tracking
git ls-files | grep requirements.txt
```

**Error: `alembic upgrade head failed`**
```bash
# Check alembic.ini exists
ls alembic.ini

# Check migrations exist
ls alembic/versions/
```

### Service Won't Start

**Error: `Module not found`**
- Check all imports in `app/main.py`
- Ensure all dependencies in `requirements.txt`

**Error: `Port binding failed`**
- Ensure using `$PORT` environment variable
- Start command: `--port $PORT` (not hardcoded)

### Database Issues

**SQLite: Data lost after redeploy**
- Expected behavior on free tier
- Upgrade to PostgreSQL for persistence

**PostgreSQL: Connection refused**
- Check environment variables match Render PostgreSQL
- Ensure same region for web service and database

## 💰 Cost Optimization

### Free Tier Limits
- 750 hours/month (enough for 1 service 24/7)
- Service sleeps after 15 min inactivity
- Cold start: ~30 seconds

### Tips
1. Use SQLite for development/demos
2. Upgrade to paid tier for always-on
3. Use PostgreSQL only when needed

## 🔗 Useful Links

- [Render Dashboard](https://dashboard.render.com/)
- [Render Documentation](https://render.com/docs)
- [Render Status](https://status.render.com/)
- [Support](https://render.com/support)

## 📝 Next Steps

After deployment:
1. ✅ Test all API endpoints
2. ✅ Update frontend to use production URL
3. ✅ Set up custom domain (optional)
4. ✅ Configure CORS properly
5. ✅ Set up monitoring and alerts
6. ✅ Create backup strategy (if using PostgreSQL)

---

**Need Help?** Open an issue on GitHub or contact support.
