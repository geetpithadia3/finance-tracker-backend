from datetime import datetime
import logging

from app.config import settings
from app.database import check_database_connection, get_database_info

logger = logging.getLogger(__name__)

class HealthService:
    def health_check(self):
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

    def get_database_info(self):
        db_info = get_database_info()
        db_status = check_database_connection()
        
        return {
            "profile": db_info["profile"],
            "is_sqlite": db_info["is_sqlite"],
            "is_postgresql": db_info["is_postgresql"],
            "connection_status": "connected" if db_status else "disconnected",
            "url_masked": db_info["url"]
        }
