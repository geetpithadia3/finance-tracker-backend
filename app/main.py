from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import logging
import time
from typing import Set
import asyncio

from app.config import settings
from app.database import create_tables
from app.routers import auth, categories, transactions, budgets, dashboard, expenses, allocation, health, budget_alerts, goals
from app.routers import rollover_config
from app.routers import recurring_transactions
from app.websockets import router as websocket_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug
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
logger.info("Starting application...")
create_tables()
logger.info("Database tables created/verified")

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
app.include_router(expenses.router)
app.include_router(allocation.router)
app.include_router(health.router)
app.include_router(budget_alerts.router)
app.include_router(rollover_config.router)
app.include_router(recurring_transactions.router)
app.include_router(websocket_router)
app.include_router(goals.router)

# Log available routes for debugging
logger.info("Available routes:")
budget_routes = []
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        route_info = f"  {list(route.methods)} {route.path}"
        logger.info(route_info)
        if '/budgets' in route.path:
            budget_routes.append(route_info)

logger.info("Budget-related routes:")
for route in budget_routes:
    logger.info(route)


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


# --- WebSocket for real-time rollover updates ---

connected_rollover_clients: Set[WebSocket] = set()

@app.websocket("/api/rollover-updates")
async def rollover_updates_ws(websocket: WebSocket):
    await websocket.accept()
    connected_rollover_clients.add(websocket)
    try:
        while True:
            # Keep the connection alive (ping/pong or sleep)
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        connected_rollover_clients.remove(websocket)

async def broadcast_rollover_update(message: dict):
    """Broadcast a rollover update to all connected clients."""
    disconnected = set()
    for ws in connected_rollover_clients:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        connected_rollover_clients.remove(ws)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=settings.debug)