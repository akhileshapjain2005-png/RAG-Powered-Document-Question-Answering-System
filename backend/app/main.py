"""Main FastAPI application."""

import hmac
import logging
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse, Response

from app.api.routes import router
from app.limiter import limiter

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173",
    ).split(",")
    if origin.strip()
]
allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
_api_key_header = os.getenv("API_KEY_HEADER_NAME", "X-API-Key")
_cors_allow_headers = [
    "Authorization",
    "Content-Type",
    "X-Request-ID",
    _api_key_header,
]

env_name = os.getenv("ENV", "development").lower()
docs_enabled = os.getenv("ENABLE_API_DOCS", "true" if env_name != "production" else "false").lower() == "true"

app = FastAPI(
    title="RAG-DocQA: AI-Powered Document Question Answering System",
    description="RAG-based document question answering system with FastAPI, ChromaDB, and OpenAI integration",
    version="1.0.0",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request id + basic security headers."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        # CSP is for HTML documents; JSON APIs should not send restrictive CSP (noise / tooling issues).
        path = request.url.path
        if not path.startswith("/api") and path != "/metrics":
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
        logging.getLogger("app.request").info(
            "%s %s -> %s (%sms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )
        return response


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=_cors_allow_headers,
)
app.add_middleware(RequestContextMiddleware)


class MetricsAuthMiddleware(BaseHTTPMiddleware):
    """Optional shared secret for /metrics (Prometheus scrape with bearer or custom header)."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path != "/metrics":
            return await call_next(request)
        token = os.getenv("METRICS_TOKEN", "").strip()
        if not token:
            return await call_next(request)
        supplied = request.headers.get("X-Metrics-Token", "")
        if not supplied:
            auth = request.headers.get("Authorization") or ""
            if auth.lower().startswith("bearer "):
                supplied = auth[7:].strip()
        if len(supplied) != len(token):
            return PlainTextResponse("Forbidden", status_code=403)
        if not hmac.compare_digest(supplied.encode("utf-8"), token.encode("utf-8")):
            return PlainTextResponse("Forbidden", status_code=403)
        return await call_next(request)


app.add_middleware(MetricsAuthMiddleware)

if os.getenv("ENABLE_METRICS", "true").lower() == "true":
    from prometheus_fastapi_instrumentator import Instrumentator

    Instrumentator().instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
    )

# Enterprise API version (stable contract). Gateways should map /api/* -> /api/v1/*.
app.include_router(router, prefix="/api/v1", tags=["api-v1"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG-DocQA: AI-Powered Document Question Answering System API",
        "version": "1.0.0",
        "api": "/api/v1",
        "docs": "/api/v1/docs" if docs_enabled else None,
        "metrics": "/metrics" if os.getenv("ENABLE_METRICS", "true").lower() == "true" else None,
    }
