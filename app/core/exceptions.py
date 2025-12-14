"""
Centralized exception handling for the application
"""
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseAppException(Exception):
    """Base exception for application-specific errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(BaseAppException):
    """Raised when input validation fails"""
    pass


class NotFoundError(BaseAppException):
    """Raised when a requested resource is not found"""
    pass


class AuthenticationError(BaseAppException):
    """Raised when authentication fails"""
    pass


class AuthorizationError(BaseAppException):
    """Raised when user lacks permission to perform action"""
    pass


class BusinessLogicError(BaseAppException):
    """Raised when business rules are violated"""
    pass


class DatabaseError(BaseAppException):
    """Raised when database operations fail"""
    pass


class ExternalServiceError(BaseAppException):
    """Raised when external service calls fail"""
    pass


# HTTP Exception Mappings
def map_exception_to_http_exception(exc: BaseAppException) -> HTTPException:
    """Map application exceptions to HTTP exceptions"""
    
    if isinstance(exc, ValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": exc.message, "details": exc.details}
        )
    
    elif isinstance(exc, NotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": exc.message, "details": exc.details}
        )
    
    elif isinstance(exc, AuthenticationError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": exc.message, "details": exc.details},
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    elif isinstance(exc, AuthorizationError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": exc.message, "details": exc.details}
        )
    
    elif isinstance(exc, BusinessLogicError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": exc.message, "details": exc.details}
        )
    
    elif isinstance(exc, DatabaseError):
        logger.error(f"Database error: {exc.message}", extra={"details": exc.details})
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "A database error occurred", "details": {}}
        )
    
    elif isinstance(exc, ExternalServiceError):
        logger.error(f"External service error: {exc.message}", extra={"details": exc.details})
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "External service unavailable", "details": {}}
        )
    
    else:
        logger.error(f"Unhandled application error: {exc.message}", extra={"details": exc.details})
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "An unexpected error occurred", "details": {}}
        )


# Common exception raising functions for convenience
def raise_not_found(resource: str, identifier: str = None) -> None:
    """Raise a not found error for a specific resource"""
    message = f"{resource} not found"
    if identifier:
        message += f" with id: {identifier}"
    raise NotFoundError(message, {"resource": resource, "identifier": identifier})


def raise_unauthorized(action: str = None) -> None:
    """Raise an authorization error"""
    message = "Access denied"
    if action:
        message += f" for action: {action}"
    raise AuthorizationError(message, {"action": action})


def raise_validation_error(field: str, message: str, value: Any = None) -> None:
    """Raise a validation error for a specific field"""
    raise ValidationError(
        f"Validation failed for {field}: {message}",
        {"field": field, "message": message, "value": value}
    )


def raise_business_error(message: str, context: Dict[str, Any] = None) -> None:
    """Raise a business logic error"""
    raise BusinessLogicError(message, context or {})

def raise_http_exception(status_code: int, detail: str, headers: Optional[Dict[str, str]] = None) -> None:
    """Raise an HTTP exception"""
    raise HTTPException(status_code=status_code, detail=detail, headers=headers)