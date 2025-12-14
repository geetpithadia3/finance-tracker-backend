from fastapi import APIRouter, Depends
from app.services.health_service import HealthService
from app.core.dependencies import get_health_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check(
    health_service: HealthService = Depends(get_health_service)
):
    """Comprehensive health check including database connectivity"""
    return health_service.health_check()


@router.get("/database")
def database_info(
    health_service: HealthService = Depends(get_health_service)
):
    """Get detailed database information"""
    return health_service.get_database_info()