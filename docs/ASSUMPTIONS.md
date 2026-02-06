# Assumptions

This file lists the assumptions made while drafting the documentation where the repository or prior answers did not provide explicit direction.

Assumption 1: The host application owns every external surface (API endpoints, CLI, job runner) and is responsible for authentication, rate limiting, and request logging; LCS runs in-process and does not expose its own server.

Assumption 2: Network egress to OpenRouter is available wherever LCS runs, and an `OPENROUTER_API_KEY` will be provided for any environment that executes real model calls; offline testing relies on mocks instead of a fallback provider.

Assumption 3: Runtime environments use Python 3.11 or newer and supply an event loop suitable for `asyncio`, because the orchestrator issues concurrent provider requests.

Assumption 4: Telemetry sinks (Prometheus scrape endpoint and OTLP collector) are optional; when they are absent, it is acceptable for metrics to remain in-process and for tracing/log export initialization to be skipped silently.

Assumption 5: Prompts and model outputs must not be persisted by LCS; any retention, redaction, or audit requirements are enforced by the host application rather than this library.

---
Maintainer/Author: Rémi Boivin (@remiboivin021)
Version: 0.1.0
Last modified: 2026-02-03
---
