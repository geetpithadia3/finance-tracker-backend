"""
Finance Tracker API V2 - Main Application Entry Point
Built on double-entry accounting principles with modern architecture
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import logging
import time

from app.config import settings
from app.database import create_tables
from app.core.logging_config import setup_logging
# Import V2 routers
from app.routers import (
    auth, transactions, categories, health, imports, reports, accounts, mappings
)

# Configure logging
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("finance_tracker.main")

app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    debug=settings.debug,
    description="Personal Finance Tracker V2 - Built on double-entry accounting with support for split transactions, auto-categorization, and CSV imports."
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Filter sensitive data from logs
    safe_params = {k: v for k, v in request.query_params.items()
                   if k.lower() not in ['password', 'token', 'secret', 'key']}
    logger.info(f"🔄 {request.method} {request.url.path} - Query: {safe_params}")

    # Process request
    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    status_icon = "✅" if response.status_code < 400 else "❌"
    logger.info(f"{status_icon} {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")

    return response

# CORS middleware with secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Type", "Authorization"]
)

# Create tables on startup
logger.info("Starting Finance Tracker V2...")

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return {
        "message": settings.app_name,
        "version": "2.0.0",
        "description": "Double-entry accounting for personal finance"
    }


@app.get("/health")
async def health_check():
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": "2.0.0"
    }


# Include V2 routers with /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(mappings.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(health.router, prefix="/api")

# Log available routes for debugging
logger.info("Available V2 API routes:")
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        logger.info(f"  {list(route.methods)} {route.path}")


# Tutorial/Documentation endpoint
@app.get("/tutorial", response_class=HTMLResponse)
def show_tutorial():
    """Display the tutorial/how-it-works page"""
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    tutorial_path = os.path.join(static_dir, "tutorial.html")

    if os.path.exists(tutorial_path):
        with open(tutorial_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="""
        <html>
        <head><title>Finance Tracker V2 Tutorial</title></head>
        <body>
        <h1>Finance Tracker V2 - Double-Entry Accounting Made Simple</h1>
        <p>Welcome to Finance Tracker V2! This personal finance management system features:</p>
        <ul>
        <li><strong>Double-Entry Accounting</strong>: Professional-grade accuracy for every transaction</li>
        <li><strong>Split Transactions</strong>: Break one purchase across multiple categories</li>
        <li><strong>Personal Share Tracking</strong>: Track shared expenses and reimbursables</li>
        <li><strong>Multiple Payment Sources</strong>: Credit cards, cash, checking accounts</li>
        <li><strong>CSV Import</strong>: Bulk import bank statements</li>
        <li><strong>Auto-Categorization</strong>: Smart pattern-based transaction categorization</li>
        <li><strong>Financial Reports</strong>: Comprehensive spending analysis</li>
        </ul>
        <p>Visit <a href="/docs">/docs</a> for complete API documentation.</p>
        </body>
        </html>
        """)


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Finance Tracker V2...")
    create_tables()
    logger.info("Database tables created/verified")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=settings.debug)
