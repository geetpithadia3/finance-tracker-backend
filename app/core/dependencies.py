
"""
Dependency injection configuration
"""
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.transaction_service import TransactionService
from app.services.category_service import CategoryService
from app.services.ledger_service import LedgerService
from app.core.security import SecurityService
import logging

logger = logging.getLogger(__name__)



# Service Dependencies
def get_security_service() -> SecurityService:
    """Get security service instance"""
    return SecurityService()

def get_transaction_service(db: Session = Depends(get_db)) -> TransactionService:
    """Get transaction service instance"""
    return TransactionService(db)





def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    """Get category service instance"""
    return CategoryService(db)

def get_ledger_service(db: Session = Depends(get_db)) -> LedgerService:
    """Get ledger service instance"""
    return LedgerService(db)

def get_auth_service(db: Session = Depends(get_db), category_service: CategoryService = Depends(get_category_service), ledger_service: LedgerService = Depends(get_ledger_service)):
    """Get auth service instance"""
    from app.services.auth_service import AuthService
    return AuthService(db, category_service, ledger_service)





def get_health_service():
    """Get health service instance"""
    from app.services.health_service import HealthService
    return HealthService()








# Context Dependencies
def get_request_context(request: Request) -> dict:
    """Get request context for logging and auditing"""
    return {
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "request_id": getattr(request.state, "request_id", None)
    }
