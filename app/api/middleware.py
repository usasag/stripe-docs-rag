"""API middleware stack: request IDs, error handling, rate limiting, timeouts."""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import AppError, SessionNotFoundError, RateLimitError, AuthenticationError


# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------

class RequestIdMiddleware(BaseHTTPMiddleware):
    """Injects ``X-Request-Id`` header on every request and response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get('X-Request-Id', str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers['X-Request-Id'] = request_id
        return response


# ---------------------------------------------------------------------------
# Error handler middleware
# ---------------------------------------------------------------------------

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Maps domain exceptions to structured JSON error responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except AuthenticationError as exc:
            return JSONResponse(
                status_code=401,
                content={'error': 'unauthorized', 'detail': str(exc)},
            )
        except RateLimitError as exc:
            return JSONResponse(
                status_code=429,
                content={'error': 'rate_limited', 'detail': str(exc)},
                headers={'Retry-After': '60'},
            )
        except SessionNotFoundError as exc:
            return JSONResponse(
                status_code=404,
                content={'error': 'not_found', 'detail': str(exc)},
            )
        except AppError as exc:
            return JSONResponse(
                status_code=400,
                content={'error': 'app_error', 'detail': str(exc)},
            )
        except Exception as exc:
            return JSONResponse(
                status_code=500,
                content={'error': 'internal', 'detail': 'An unexpected error occurred'},
            )


# ---------------------------------------------------------------------------
# Rate limiter middleware (in-process token bucket per IP)
# ---------------------------------------------------------------------------

class _TokenBucket:
    """Simple token-bucket rate limiter."""

    def __init__(self, rate: float, burst: int) -> None:
        self.rate = rate  # tokens per second
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()

    def consume(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-process per-IP token-bucket rate limiter.

    Defaults: 30 requests/minute burst, 0.5 requests/second sustained.
    """

    def __init__(self, app, rate: float = 0.5, burst: int = 30) -> None:
        super().__init__(app)
        self.rate = rate
        self.burst = burst
        self._buckets: dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(self.rate, self.burst)
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path == '/health':
            return await call_next(request)

        client_ip = request.client.host if request.client else 'unknown'
        bucket = self._buckets[client_ip]
        if not bucket.consume():
            return JSONResponse(
                status_code=429,
                content={'error': 'rate_limited', 'detail': 'Too many requests'},
                headers={'Retry-After': '60'},
            )
        return await call_next(request)
