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
    "provider_breaker_open_total",
    "provider_breaker_state",
    "policy_reload_total",
    "policy_reload_duration_seconds",
    "policy_active_info",
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
    ["strategy"],
)

quality_score = Histogram(
    "quality_score",
    "Code-quality derived scores per model",
    ["strategy", "metric", "outcome"],
    buckets=[0.0, 0.25, 0.5, 0.75, 1.0],
)

quality_score_stats = Gauge(
    "quality_score_stats",
    "Aggregated overall quality score statistics by request",
    ["strategy", "stat"],
)

policy_reload_total = Counter(
    "policy_reload_total",
    "Count of policy reload attempts",
    ["outcome", "source", "reason"],
)

policy_reload_duration_seconds = Histogram(
    "policy_reload_duration_seconds",
    "Duration of policy reload attempts",
    ["source"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5],
)

policy_active_info = Gauge(
    "policy_active_info",
    "Information about the currently active policy",
    ["policy_id", "gating_mode"],
)

provider_breaker_open_total = Counter(
    "provider_breaker_open_total",
    "Times a provider circuit breaker opened",
    ["model", "reason"],
)

provider_breaker_state = Gauge(
    "provider_breaker_state",
    "Current breaker state by model (0=closed,0.5=half_open,1=open)",
    ["model"],
)


def render_metrics() -> bytes:
    return generate_latest()
