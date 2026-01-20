from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, CONTENT_TYPE_LATEST, generate_latest

__all__ = [
    "CONTENT_TYPE_LATEST",
    "render_metrics",
    "http_request_duration_seconds",
    "http_requests_total",
    "llm_call_duration_seconds",
    "llm_calls_total",
    "consensus_duration_seconds",
    "quality_score",
    "quality_score_stats",
]

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Duration of HTTP requests in seconds",
    ["route", "method", "status"],
)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["route", "method", "status"],
)

llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds",
    "Duration of LLM provider calls in seconds",
    ["model", "outcome"],
)

llm_calls_total = Counter(
    "llm_calls_total",
    "Total LLM provider calls",
    ["model", "outcome"],
)

consensus_duration_seconds = Histogram(
    "consensus_duration_seconds",
    "Duration of consensus computation in seconds",
    ["mode"],
)

quality_score = Histogram(
    "quality_score",
    "Code-quality derived scores per model",
    ["mode", "metric", "outcome"],
    buckets=[0.0, 0.25, 0.5, 0.75, 1.0],
)

quality_score_stats = Gauge(
    "quality_score_stats",
    "Aggregated overall quality score statistics by request",
    ["mode", "stat"],
)


def render_metrics() -> bytes:
    return generate_latest()
