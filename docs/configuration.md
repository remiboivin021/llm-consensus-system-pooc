# Configuration

This file describes how LCS reads configuration, which knobs matter at runtime, and how to confirm your values are loaded as intended.

LCS relies on Pydantic Settings (`src.config.Settings`) with `.env` support and sensible defaults. Environment variables are parsed on first access and cached for the process lifetime.

Key environment variables and defaults:
- `OPENROUTER_API_KEY` (no default): bearer token passed to OpenRouter; omit it only for offline testing where provider calls are mocked.
- `OPENROUTER_BASE_URL` (default `https://openrouter.ai/api/v1`): base URL for the provider transport.
- `DEFAULT_MODELS` (default `["qwen/qwen3-coder:free", "mistralai/devstral-2512:free", "xiaomi/mimo-v2-flash:free"]`): comma-separated list or JSON-like list of model identifiers used when a request omits `models`.
- `PROVIDER_TIMEOUT_MS` (default `5000`): per-model HTTP timeout in milliseconds.
- `E2E_TIMEOUT_MS` (default `10000`): overall orchestration timeout; exceeded requests raise a timeout envelope.
- `MAX_PROMPT_CHARS` (default `8000`): upper bound checked against both policy and settings.
- `MAX_MODELS` (default `5`): guardrail for concurrent model calls.
- `LOG_LEVEL` (default `INFO`): controls structlog root level.
- `OTEL_EXPORTER_OTLP_ENDPOINT` (default `http://otel-collector:4318`): used only if you enable tracing or logging export.
- `SERVICE_NAME` (default `LCS`): propagated to telemetry resources.
- `POLICY_FILE` (no default): optional path to a YAML policy; when absent the built-in `policies/default.policy.yaml` is used.

Policy configuration lives in YAML and mirrors `src.policy.models.Policy`. Guardrails cover prompt length and model limits; gating rules can require a winner, minimum confidence, or minimum quality score. Set `gating_mode` to `shadow` to annotate decisions without blocking, or `soft` to gate responses.

Validate configuration by running `poetry run pytest tests/unit/test_config_parse.py` and `poetry run pytest tests/unit/test_policy_loader.py`. To inspect values directly, run `poetry run python - <<'PY'\nfrom src.config import get_settings\nprint(get_settings().model_dump())\nPY` and confirm outputs match expectations.

---
Maintainer/Author: Rémi Boivin (@remiboivin021)
Version: 0.1.0
Last modified: 2026-02-03
---
