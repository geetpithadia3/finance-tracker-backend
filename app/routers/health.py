from fastapi import APIRouter
from datetime import datetime

from app.config import settings
from app.database import check_database_connection, get_database_info

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    """Comprehensive health check including database connectivity"""
    db_status = check_database_connection()
    db_info = get_database_info()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "version": settings.version,
        "database": {
            "profile": db_info["profile"],
            "connection": "connected" if db_status else "disconnected",
            "url_masked": db_info["url"]
        }
    }


@router.get("/database")
def database_info():
    """Get detailed database information"""
    db_info = get_database_info()
    db_status = check_database_connection()
    
    return {
        "profile": db_info["profile"],
        "is_sqlite": db_info["is_sqlite"],
        "is_postgresql": db_info["is_postgresql"],
        "connection_status": "connected" if db_status else "disconnected",
        "url_masked": db_info["url"]
    }