"""
Prometheus Metrics

Defines application-level metrics for monitoring and alerting.

Metrics exposed:
- http_requests_total: Counter of all HTTP requests (by method, path, status)
- http_request_duration_seconds: Histogram of request latency
- http_requests_in_progress: Gauge of currently active requests

These are scraped by Prometheus via the GET /metrics endpoint and visualized
in Grafana dashboards. Standard labels (method, path, status_code) enable
flexible querying like "p99 latency for POST /ml/train" or
"error rate on /auth/login in the last 5 minutes."

Why Prometheus (pull-based) over push-based metrics (StatsD, Datadog)?
- Zero external dependency at startup (no agent needed to begin collecting)
- Industry standard for cloud-native apps (K8s has built-in Prometheus support)
- Free & self-hosted (vs. per-host pricing of commercial APM tools)
- Grafana integration is free and excellent
"""

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

# ─── Metric Definitions ────────────────────────────────────────

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method"],
)


def _normalize_path(path: str) -> str:
    """
    Normalize request paths to avoid high-cardinality label explosion.

    Prometheus labels must be low-cardinality. Without normalization,
    paths like /datasets/1, /datasets/2, /datasets/3 would each create
    a separate time series — leading to memory issues at scale.

    Strategy: replace numeric path segments with {id}.
    """
    parts = path.split("/")
    normalized = []
    for part in parts:
        if part.isdigit():
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized)


# ─── Metrics Middleware ────────────────────────────────────────

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Instruments all HTTP requests with Prometheus metrics.

    Records:
    - Total request count (by method, normalized path, status code)
    - Request duration histogram (for latency percentiles: p50, p95, p99)
    - In-progress request gauge (for concurrency monitoring)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method
        path = _normalize_path(request.url.path)

        # Skip metrics for the /metrics endpoint itself (avoid self-referential noise)
        if request.url.path == "/metrics":
            return await call_next(request)

        REQUESTS_IN_PROGRESS.labels(method=method).inc()
        start = time.monotonic()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.monotonic() - start
            REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()
            REQUEST_DURATION.labels(method=method, path=path).observe(duration)
            REQUESTS_IN_PROGRESS.labels(method=method).dec()

        return response


# ─── Metrics Endpoint ──────────────────────────────────────────

def metrics_endpoint(request: Request) -> StarletteResponse:
    """
    GET /metrics — Prometheus scrape endpoint.

    Returns metrics in Prometheus text exposition format.
    This endpoint is NOT behind authentication (Prometheus needs to
    scrape it without tokens). In production, restrict access via
    network policy or reverse proxy rules.
    """
    return StarletteResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
