# Error handling utilities for the application
"""
Provides a thin wrapper to expose exception handling helpers.
The original implementations live in `app.core.exceptions`. This module
re‑exports the public functions so that imports like
`from app.core.error_handler import raise_http_exception` work without
modifying existing service code.
"""

from .exceptions import (
    BaseAppException,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    DatabaseError,
    ExternalServiceError,
    map_exception_to_http_exception,
    raise_not_found,
    raise_unauthorized,
    raise_validation_error,
    raise_business_error,
    raise_http_exception,
)

__all__ = [
    "BaseAppException",
    "ValidationError",
    "NotFoundError",
    "AuthenticationError",
    "AuthorizationError",
    "BusinessLogicError",
    "DatabaseError",
    "ExternalServiceError",
    "map_exception_to_http_exception",
    "raise_not_found",
    "raise_unauthorized",
    "raise_validation_error",
    "raise_business_error",
    "raise_http_exception",
]
