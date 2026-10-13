import logging
import re
from typing import Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.config import get_settings

logger = logging.getLogger("backend.security")

# Maximum permitted HTTP request body size: 64 KB
MAX_BODY_SIZE_BYTES = 64 * 1024

# Redaction patterns for secrets in logs
OPENROUTER_KEY_REGEX = re.compile(r"sk-or-[A-Za-z0-9_\-]+", re.IGNORECASE)
BEARER_REGEX = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", re.IGNORECASE)
TOKEN_HEADER_REGEX = re.compile(r"(X-Run-Token:\s*)[A-Za-z0-9_\-]+", re.IGNORECASE)


class RedactingFilter(logging.Filter):
    """Logging filter that scrubs API keys and authentication tokens."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = OPENROUTER_KEY_REGEX.sub("sk-or-[REDACTED]", record.msg)
            record.msg = BEARER_REGEX.sub(r"\1[REDACTED]", record.msg)
            record.msg = TOKEN_HEADER_REGEX.sub(r"\1[REDACTED]", record.msg)
        if record.args:
            clean_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    clean = OPENROUTER_KEY_REGEX.sub("sk-or-[REDACTED]", arg)
                    clean = BEARER_REGEX.sub(r"\1[REDACTED]", clean)
                    clean = TOKEN_HEADER_REGEX.sub(r"\1[REDACTED]", clean)
                    clean_args.append(clean)
                else:
                    clean_args.append(arg)
            record.args = tuple(clean_args)
        return True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds hardened OWASP security headers to all HTTP responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects incoming HTTP requests whose payload exceeds 64 KB."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_BODY_SIZE_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "payload_too_large",
                            "detail": "Request body exceeds maximum size of 64KB.",
                        },
                    )
            except ValueError:
                pass

        body = await request.body()
        if len(body) > MAX_BODY_SIZE_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "payload_too_large",
                    "detail": "Request body exceeds maximum size of 64KB.",
                },
            )

        return await call_next(request)


# Global rate limiter using client IP
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
    headers_enabled=False,
)


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded", "detail": f"Rate limit exceeded: {exc.detail}"},
    )


def setup_security(app: FastAPI) -> None:
    """Configures CORS, headers, trusted host, body limits, and logging redaction."""
    settings = get_settings()

    # 1. Attach Logging Redaction Filter to root and uvicorn loggers
    redactor = RedactingFilter()
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        log_instance = logging.getLogger(name)
        if not any(isinstance(f, RedactingFilter) for f in log_instance.filters):
            log_instance.addFilter(redactor)

    # 2. Strict CORS
    # Require exact origin; reject wildcard
    frontend_origin = settings.FRONTEND_ORIGIN.strip()
    if frontend_origin == "*":
        logger.warning("FRONTEND_ORIGIN cannot be '*' in hardened mode. Defaulting to http://localhost:5173.")
        frontend_origin = "http://localhost:5173"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Run-Token", "Last-Event-ID"],
    )

    # 3. TrustedHostMiddleware for localhost and tests
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "test", "testserver"],
    )

    # 4. Custom Security Headers & Body Limit Middlewares
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)

    # 5. Rate limiting configuration
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

    # 6. Generic exception handler for production
    if settings.APP_ENV == "prod":
        @app.exception_handler(Exception)
        async def generic_exception_handler(request: Request, exc: Exception):
            if isinstance(exc, HTTPException):
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"detail": exc.detail},
                    headers=exc.headers,
                )
            logger.error(f"Internal server error: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error"},
            )
