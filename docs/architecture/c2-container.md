# C2 — Container

This view describes the deployable units around LCS and how they communicate.

The LCS container is a pure Python library loaded into the host process. It exposes an asynchronous API (`LcsClient.run`) and depends on configuration supplied through environment variables and an optional policy file. It opens outbound HTTPS connections to the OpenRouter API using httpx; concurrency is managed with asyncio tasks and a semaphore sized by `MAX_MODELS`.

Host applications form their own containers: for example, a FastAPI service that exposes a `/consensus` route or a background worker that evaluates prompts in batch. These containers own authentication, multi-tenancy, and any persistence of prompts or model outputs. When telemetry is enabled, the host also exposes a metrics endpoint that calls `render_metrics()` and forwards logs/traces to an OTLP collector.

No additional runtime containers are required; SQLite and other storage mentioned in earlier plans are not part of the current implementation. If you later add a network API container, keep it thin and delegate all consensus logic to this library so the boundary stays clean.

Validate container wiring by running `poetry run pytest tests/unit/test_transport.py tests/unit/test_orchestrator_metrics.py` to cover outbound calls and metrics emission. In an integrated service, confirm that OpenRouter traffic flows and that your metrics endpoint returns Prometheus-formatted data.

---
Maintainer/Author: Rémi Boivin (@remiboivin021)
Version: 0.1.0
Last modified: 2026-02-03
---
