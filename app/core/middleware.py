"""
Custom middleware for the application
"""
from fastapi import Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from app.core.exceptions import BaseAppException, map_exception_to_http_exception
import logging
import time
import uuid

logger = logging.getLogger(__name__)


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle application exceptions and convert them to HTTP responses"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
            return response
        except BaseAppException as exc:
            # Convert application exceptions to HTTP exceptions
            http_exc = map_exception_to_http_exception(exc)
            # Log the original exception for debugging
            logger.warning(f"Application exception: {exc.message}", extra={
                "exception_type": type(exc).__name__,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method
            })
            raise http_exc
        except HTTPException:
            # Re-raise FastAPI HTTP exceptions as-is
            raise
        except Exception as exc:
            # Log unexpected exceptions
            logger.error(f"Unexpected exception: {str(exc)}", extra={
                "exception_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method
            }, exc_info=True)
            # Return generic 500 error
            raise HTTPException(status_code=500, detail="An unexpected error occurred")


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to track requests and add request IDs"""
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track request performance"""
    
    def __init__(self, app, slow_request_threshold: float = 2.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests
        if process_time > self.slow_request_threshold:
            logger.warning(f"Slow request detected", extra={
                "path": request.url.path,
                "method": request.method,
                "process_time": process_time,
                "status_code": response.status_code,
                "request_id": getattr(request.state, "request_id", None)
            })
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses"""
    
    def __init__(self, app, additional_headers: dict = None):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "X-Robots-Tag": "noindex",
            **(additional_headers or {})
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Enhanced request logging middleware with privacy protection"""
    
    def __init__(self, app, sensitive_params: set = None):
        super().__init__(app)
        self.sensitive_params = sensitive_params or {
            'password', 'token', 'secret', 'key', 'authorization'
        }
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        
        # Filter sensitive data from query params
        safe_params = {
            k: v for k, v in request.query_params.items() 
            if k.lower() not in self.sensitive_params
        }
        
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.info(f"🔄 Request started", extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": safe_params,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", "unknown")[:100]  # Truncate long user agents
        })
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        status_icon = "✅" if response.status_code < 400 else "❌"
        
        logger.info(f"{status_icon} Request completed", extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": round(process_time, 3),
            "response_size": response.headers.get("content-length", "unknown")
        })
        
        return response