from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database import create_tables
from app.routers import (
    auth,
    categories,
    transactions,
    budgets,
    dashboard,
    recurring_transactions,
    expenses,
    allocation,
    health
)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://finance-tracker-frontend-7131.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Create tables on startup
create_tables()

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return {"message": settings.app_name, "version": settings.version}


@app.get("/health")
async def health_check():
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name
    }


# Include routers
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(dashboard.router)
app.include_router(recurring_transactions.router)
app.include_router(expenses.router)
app.include_router(allocation.router)
app.include_router(health.router)


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
        <head><title>Finance Tracker Tutorial</title></head>
        <body>
        <h1>Finance Tracker Tutorial</h1>
        <p>Welcome to Finance Tracker! This comprehensive personal finance management system includes:</p>
        <ul>
        <li>Category-based transaction tracking</li>
        <li>Advanced budget management with category limits</li>
        <li>Smart allocation system</li>
        <li>Recurring transactions with flexible scheduling</li>
        <li>Month-based analytics and reporting</li>
        </ul>
        <p>Visit <a href="/docs">/docs</a> for complete API documentation.</p>
        </body>
        </html>
        """)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=settings.debug)