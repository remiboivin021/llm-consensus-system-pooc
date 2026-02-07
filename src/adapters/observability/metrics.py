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
    "run_event_callback_total",
    "run_event_callback_duration_seconds",
    "run_events_total",
    "early_stop_samples_used",
    "early_stop_decisions_total",
    "early_stop_confidence",
    "prompt_safety_decisions_total",
    "prompt_safety_duration_seconds",
    "quality_score",
    "quality_score_stats",
    "provider_breaker_open_total",
    "provider_breaker_state",
    "policy_reload_total",
    "policy_reload_duration_seconds",
    "policy_active_info",
    "provider_resolution_failures_total",
    "preamble_usage_total",
    "pii_redaction_runs_total",
    "pii_redactions_total",
    "output_validation_total",
    "output_validation_reasks_total",
    "gate_decisions_total",
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
    ["provider", "model", "outcome"],
)

llm_calls_total = Counter(
    "llm_calls_total",
    "Total LLM provider calls",
    ["provider", "model", "outcome"],
)

consensus_duration_seconds = Histogram(
    "consensus_duration_seconds",
    "Duration of consensus computation in seconds",
    ["strategy"],
)

run_event_callback_total = Counter(
    "run_event_callback_total",
    "Total run-event callbacks",
    ["outcome"],
)

run_event_callback_duration_seconds = Histogram(
    "run_event_callback_duration_seconds",
    "Duration of run-event callbacks in seconds",
    ["outcome"],
)

run_events_total = Counter(
    "run_events_total",
    "Total consensus runs by outcome",
    ["outcome"],
)

early_stop_samples_used = Histogram(
    "early_stop_samples_used",
    "Samples consumed before stopping early",
    ["strategy"],
    buckets=[1, 2, 3, 4, 5, 8, 10],
)

early_stop_decisions_total = Counter(
    "early_stop_decisions_total",
    "Early-stop outcomes",
    ["strategy", "reason"],
)

early_stop_confidence = Histogram(
    "early_stop_confidence",
    "Consensus confidence observed at stop",
    ["strategy"],
    buckets=[0.0, 0.25, 0.5, 0.66, 0.75, 0.85, 0.95, 1.0],
)

prompt_safety_decisions_total = Counter(
    "prompt_safety_decisions_total",
    "Prompt safety decisions by mode/reason",
    ["mode", "action", "reason"],
)

prompt_safety_duration_seconds = Histogram(
    "prompt_safety_duration_seconds",
    "Prompt safety detector duration",
    ["mode"],
    buckets=[0.001, 0.005, 0.01, 0.02, 0.05],
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

provider_resolution_failures_total = Counter(
    "provider_resolution_failures_total",
    "Total provider resolution failures (unknown provider, unsupported model, etc.)",
    ["reason"],
)

gate_decisions_total = Counter(
    "gate_decisions_total",
    "Total gating decisions by stage and reason",
    ["stage", "reason"],
)

output_validation_total = Counter(
    "output_validation_total",
    "Outcome of output validation checks",
    ["outcome", "reason"],
)

output_validation_reasks_total = Counter(
    "output_validation_reasks_total",
    "Count of validation-triggered re-asks",
    ["outcome"],
)

pii_redaction_runs_total = Counter(
    "pii_redaction_runs_total",
    "Count of PII redaction executions",
    ["applied"],
)

pii_redactions_total = Counter(
    "pii_redactions_total",
    "Total redacted PII occurrences by type",
    ["type"],
)

preamble_usage_total = Counter(
    "preamble_usage_total",
    "Preamble selection outcomes",
    ["key", "outcome"],
)


def render_metrics() -> bytes:
    return generate_latest()
