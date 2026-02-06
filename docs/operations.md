# Operations

This document explains how to run LCS in production-like environments, with attention to observability, resiliency, and safe degradation when providers misbehave.

Observability: metrics are defined in `src.adapters.observability.metrics` using Prometheus primitives. Call `render_metrics()` from your host process and expose the bytes on an HTTP endpoint of your choice. Key series include `llm_calls_total` and `llm_call_duration_seconds` (per model and outcome), `consensus_duration_seconds` (per strategy), and `quality_score`/`quality_score_stats` when scoring is enabled. Structured logging uses structlog; OpenTelemetry log export is available if an OTLP endpoint is configured. Tracing can be attached to a FastAPI app via `src.adapters.observability.tracing.configure_tracing(app, service_name, endpoint)` and will also instrument httpx calls to the provider.

Resiliency: the orchestrator enforces per-provider and end-to-end timeouts, limits concurrent model calls with a semaphore sized by `MAX_MODELS`, and tolerates individual call failures by returning `ErrorEnvelope` instances per model. Policy gating can short-circuit before calling providers (prompt length, model allowlist) or after judging if confidence or quality is too low; in `shadow` mode it records the reason without blocking.

Data handling: prompts and responses stay in memory; LCS does not persist or redact them. Metrics record counts, durations, and aggregate scores but never log full prompt text. Your host application is responsible for any additional logging or audit requirements.

Validate operational wiring by running `poetry run pytest tests/unit/test_metrics.py tests/unit/test_policy_enforcer.py tests/unit/test_orchestrator.py`. In a live process, hit the metrics endpoint you expose and confirm Prometheus can scrape it; if tracing is enabled, verify spans reach the collector and include attributes `request_id` and `model_count`.

---
Maintainer/Author: Rémi Boivin (@remiboivin021)
Version: 0.1.0
Last modified: 2026-02-03
---
