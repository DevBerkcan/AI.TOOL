"""Custom middleware for tenant isolation and request logging."""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.core.security import validate_token

logger = structlog.get_logger()

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/callback",
}


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract tenant context from JWT and attach to request state."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth for public paths
        if request.url.path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        try:
            user = await validate_token(request)
            request.state.user = user
            request.state.tenant_id = user.tenant_id
        except Exception:
            # Let the route handler deal with auth errors
            request.state.user = None
            request.state.tenant_id = None

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing and request ID."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.info(
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            user=getattr(getattr(request.state, "user", None), "email", None),
        )

        response.headers["X-Request-ID"] = request_id
        return response
