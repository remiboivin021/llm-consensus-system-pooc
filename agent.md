Codex Build Instructions (Python-only LLM Consensus + Observability)

## 0) Objective

Generate a complete, working **Python-only** monorepo named `lcs` that implements:

1. **LLM consensus service** (majority vote via similarity scoring; debate mode scaffold ready).
2. **FastAPI API** (`/v1/consensus`, `/health`, `/ready`, `/metrics`).
3. **CLI** Typer preferred.
4. **Contracts** (Pydantic models) as the single source of truth for request/response/error.
5. **Observability stack** with Docker Compose:
   - **Prometheus** (scrapes app `/metrics`)
   - **Grafana** (datasources provisioned)
   - **Loki** (logs backend)
   - **Tempo** (traces backend)
   - **OpenTelemetry Collector** (OTLP receiver; exports traces → Tempo, logs → Loki)
6. **TDD** test suite (unit + integration) using mocks (no real OpenRouter calls).
7. **Quality gates**: ruff, black, pytest, (optional mypy).

### Non-goals (YAGNI)
- No Rust, no PyO3, no custom web dashboard.
- No DB, no user management, no advanced debate algorithm beyond scaffolding.
- No production deployment manifests (k8s) in MVP.

---

## 1) Engineering Principles (Mandatory)

### KISS
- Prefer the simplest working implementation.
- Avoid over-abstraction. Keep modules small and explicit.

### YAGNI
- Implement only what is required for the MVP to run and be testable end-to-end.
- Debate mode may be a stub returning `501 Not Implemented` unless explicitly wired.

### DbC (Design by Contract)
- Validate all external inputs at boundaries:
  - FastAPI request bodies validated by Pydantic.
  - Config validated at startup.
  - Model list length and prompt constraints enforced.
- If a contract is violated, return a deterministic error envelope.

### Defensive Programming
- Timeouts everywhere (provider calls, request-level E2E timeout).
- Handle partial failures (one model errors should not crash consensus).
- Normalize errors into stable error types.

### TDD
- Implement tests first where feasible.
- Every module has at least one unit test.
- Integration tests cover API + mocked provider.

---

## 2) Repository Layout (Must Match)

Create this exact structure:

```
lcs/
├── agent.md
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── .ruff.toml
├── .pre-commit-config.yaml
├── docker-compose.yml
├── docker/
│   ├── prometheus/
│   │   └── prometheus.yml
│   ├── otel/
│   │   └── otel-collector-config.yaml
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/
│       │   │   └── datasources.yaml
│       │   └── dashboards/
│       │       └── dashboards.yaml
│       └── dashboards/
│           └── api_overview.json
├── sample/
│   ├── __init__.py
│   ├── config.py
│   ├── contracts/
│   │   ├── __init__.py
│   │   ├── request.py
│   │   ├── response.py
│   │   ├── errors.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── consensus.py
│   │   ├── similarity.py
│   │   ├── embeddings.py
│   │   ├── models.py
│   │   └── timeouts.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── openrouter.py
│   │   └── transport.py
│   ├── observability/
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   ├── tracing.py
│   │   └── metrics.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── routes.py
│   │   └── middleware.py
│   └── cli/
│       ├── __init__.py
│       └── main.py
└── tests/
    ├── __init__.py
    ├── unit/
    │   ├── test_similarity.py
    │   ├── test_consensus.py
    │   ├── test_contracts.py
    │   └── test_provider_mock.py
    ├── integration/
    │   └── test_api_consensus.py
    └── fixtures/
        ├── __init__.py
        └── openrouter_responses.py
```
---

## 3) Tooling and Dependencies (Pin sensibly)

Use **Python 3.11+**. Use **Poetry**.

### `pyproject.toml` dependencies (minimum)
- `fastapi`
- `uvicorn[standard]`
- `pydantic`
- `pydantic-settings`
- `httpx`
- `prometheus-client`
- `structlog`
- `python-dotenv`
- `jinja2` (templates placeholder; minimal)
- `opentelemetry-api`
- `opentelemetry-sdk`
- `opentelemetry-exporter-otlp`
- `opentelemetry-instrumentation-fastapi`
- `opentelemetry-instrumentation-httpx`
- `typer`

### Dev dependencies
- `pytest`
- `pytest-asyncio`
- `respx` (httpx mocking)
- `ruff`
- `black`
- (optional) `mypy`

---

## 4) Configuration (DbC)

### `.env.example` (exact keys)
- `OPENROUTER_API_KEY=`
- `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1/chat/completions`
- `DEFAULT_MODELS=qwen/qwen3-coder:free,mistralai/devstral-2512:free,xiaomi/mimo-v2-flash:free`
- `DEFAULT_JUDGE=meta-llama/llama-3.1-70b-instruct:free`
- `PROVIDER_TIMEOUT_MS=5000`
- `E2E_TIMEOUT_MS=10000`
- `MAX_PROMPT_CHARS=10000`
- `LOG_LEVEL=INFO`
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`
- `SERVICE_NAME=LCS`

### `LCS/config.py`
- Use `pydantic-settings`.
- Validate:
  - `DEFAULT_MODELS` is non-empty list.
  - timeouts are positive ints.
  - max prompt chars positive.
- Provide `Settings.load()` and a cached singleton.

---

## 5) Contracts (Single Source of Truth)

### `contracts/request.py`
Create `ConsensusRequest` with:
- `request_id: str` (default uuid4 string)
- `prompt: str` (min 1 char, max `MAX_PROMPT_CHARS` enforced at API boundary)
- `models: list[str]` (default from config; enforce length >= 1, recommend 3)
- `mode: Literal["majority", "debate"]` (default "majority")
- `include_raw: bool = True`

### `contracts/response.py`
Create:
- `ModelResponse`:
  - `model: str`
  - `content: str | None`
  - `latency_ms: int | None`
  - `error: ErrorEnvelope | None`
- `ConsensusResult`:
  - `request_id: str`
  - `winner: str | None`
  - `confidence: float` (0.0–1.0)
  - `responses: list[ModelResponse]`
  - `method: str` (e.g. "majority_cosine")
  - `timing: { e2e_ms: int }`

### `contracts/errors.py`
`ErrorEnvelope`:
- `type: Literal["timeout","http_error","rate_limited","invalid_response","config_error","internal"]`
- `message: str`
- `retryable: bool = False`
- `status_code: int | None = None`

All contracts must be JSON-serializable and have `.model_dump()` stable output.

---

## 6) Core Logic (KISS + Defensive)

### `core/similarity.py`
- Implement cosine similarity for vectors of floats.
- Provide `cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float`
- Unit tests with known vectors:
  - identical → 1.0
  - orthogonal → 0.0 (or ~0)

### `core/embeddings.py`
KISS MVP:
- Do **not** implement real embeddings.
- Implement a deterministic **cheap embedding** for similarity:
  - Tokenize by whitespace
  - Hash tokens into a fixed-size vector (e.g. 128 dims) with simple hashing
  - Normalize vector
This avoids external dependency and keeps tests deterministic.

### `core/consensus.py`
Implement majority-by-similarity:
1. For each model response content (non-error), compute embedding vector.
2. Compute pairwise cosine similarity matrix.
3. Score each response as mean similarity to others (ignore missing/errored).
4. Winner = highest score.
5. Confidence = clamp((top1 - top2 + 1) / 2) or a simple normalized delta; must be stable and in [0,1].
6. If fewer than 1 successful response:
   - winner = None
   - confidence = 0.0
   - return responses with errors

Defensive rules:
- A single provider failure must not crash the request.
- If only one success, winner is that response, confidence low (e.g. 0.33).

### `core/timeouts.py`
- Provide helper to enforce E2E timeout using `asyncio.wait_for`.

### `core/models.py`
- Dataclasses or small helpers only; do not duplicate Pydantic contracts.

---

## 7) Provider Layer (OpenRouter via httpx)

### `providers/transport.py`
- Build a single `httpx.AsyncClient` factory with sensible defaults:
  - timeout from settings (seconds)
  - headers include authorization (Bearer)
- Provide `async def close()` hook (FastAPI lifespan).

### `providers/openrouter.py`
- Implement:
  - `async def call_model(prompt: str, model: str, request_id: str) -> tuple[str, latency_ms]`
- Endpoint path: `/chat/completions` (OpenAI-compatible shape).
- Return string content from response JSON.
- Normalize errors into `ErrorEnvelope`:
  - 429 → `rate_limited`
  - timeout → `timeout`
  - other 4xx/5xx → `http_error`
  - malformed JSON → `invalid_response`

**Important**: For tests, all HTTP calls must be mockable via `respx`.

---

## 8) Observability (OTel + Prometheus + Logs)

### `observability/logging.py`
- Configure `structlog` to output JSON to stdout.
- Include fields:
  - `service`, `request_id`, `route`, `latency_ms`, `model`, `error_type`, `trace_id` (if available)

### `observability/metrics.py`
Use `prometheus-client`:
- Histogram:
  - `http_request_duration_seconds{route,method,status}`
  - `llm_call_duration_seconds{model,outcome}`
  - `consensus_duration_seconds{mode}`
- Counter:
  - `http_requests_total{route,method,status}`
  - `llm_calls_total{model,outcome}`
- Provide `render_metrics()` and FastAPI endpoint wiring.

### `observability/tracing.py`
- Configure OpenTelemetry SDK.
- Use OTLP HTTP exporter to `OTEL_EXPORTER_OTLP_ENDPOINT`.
- Set resource `service.name` from settings.
- Instrument:
  - FastAPI
  - httpx
- Ensure trace context can be correlated (best-effort).

---

## 9) FastAPI API (Minimal, Correct)

### `api/app.py`
- Create FastAPI app with:
  - lifespan: init settings, logging, tracing, provider client
  - include router
  - add middleware for request metrics + request_id injection

### `api/routes.py`
Endpoints:
- `GET /health` → 200 {"status":"ok"}
- `GET /ready` → 200 (checks settings loaded)
- `GET /metrics` → Prometheus text format
- `POST /v1/consensus`:
  - body: `ConsensusRequest`
  - enforce max prompt length (DbC)
  - apply E2E timeout
  - call provider in parallel (`asyncio.gather`)
  - call consensus scoring
  - return `ConsensusResult`

### `api/middleware.py`
- Inject `request_id` header if absent; propagate to logs and response.
- Measure latency and record Prometheus metrics.
- Handle exceptions into `ErrorEnvelope` (500 internal) with consistent JSON response.

---

## 10) CLI

### `cli/main.py`
Implement Typer command:
- `consensus --prompt "..." --models "a,b,c" --mode majority --include-raw true`
- Calls API if `API_URL` provided, otherwise calls core directly (KISS: call core directly to avoid network requirement).
- Print JSON output.

---

## 11) Docker Compose (Observability Stack + App)

### `docker-compose.yml`
Services:
- `app` (FastAPI)
- `prometheus`
- `grafana`
- `loki`
- `tempo`
- `otel-collector`

Requirements:
- app exposes `8000`
- prometheus scrapes `app:8000/metrics`
- otel collector listens OTLP HTTP on `4318`
- grafana provision datasources automatically:
  - Prometheus
  - Loki
  - Tempo

### `docker/prometheus/prometheus.yml`
- One scrape job for `app:8000`

### `docker/otel/otel-collector-config.yaml`
- receivers: otlp (http)
- exporters: loki, tempo
- pipelines:
  - traces: otlp → tempo
  - logs: otlp → loki
Keep it minimal and working.

### Grafana provisioning
- `datasources.yaml`: define Prometheus, Loki, Tempo.
- `dashboards.yaml`: load `api_overview.json`.
- `api_overview.json`: minimal panels (RPS, error rate, p95 latency, llm latency by model).
KISS: do not overbuild dashboards.

---

## 12) Tests (TDD, No External Calls)

### Unit tests
- `test_similarity.py`: cosine correctness
- `test_consensus.py`: winner selection and confidence bounds
- `test_contracts.py`: pydantic validation and stable serialization
- `test_provider_mock.py`: openrouter client parsing + error mapping (with respx)

### Integration test
- `test_api_consensus.py`:
  - Use FastAPI TestClient or httpx AsyncClient with ASGI app
  - Mock OpenRouter calls via respx to return 3 different outputs
  - Assert:
    - 200 response
    - `request_id` returned
    - `responses` length matches models
    - `winner` is expected
    - metrics endpoint returns text with expected metric names

**Rule**: test suite must pass offline.

---

## 13) Make It Run (Commands)

Provide in README:

### Local
- `poetry install`
- `poetry run uvicorn consensus_llm.api.app:app --host 0.0.0.0 --port 8000`

### Tests
- `poetry run pytest -q`

### Lint/Format
- `poetry run ruff check .`
- `poetry run black --check .`

### Docker
- `docker compose up --build`

---

## 14) Definition of Done (DoD) — Global

The project is considered successfully generated when:

1. `poetry install` completes without errors.
2. `poetry run pytest` passes.
3. `poetry run ruff check .` passes.
4. `poetry run black --check .` passes.
5. `docker compose up --build` starts all services.
6. Grafana is reachable, datasources exist, and Prometheus panels show data after one API call.
7. A `POST /v1/consensus` works with mocked OpenRouter in tests and real OpenRouter in runtime (if key is set).

---

## 15) Implementation Order (Must Follow)

1. Create repo structure + config + contracts + core similarity/embeddings/consensus with unit tests.
2. Implement provider client + provider tests (respx).
3. Implement FastAPI app/routes/middleware + integration test.
4. Add metrics + `/metrics`.
5. Add tracing setup + OTLP exporter (ensure it does not break if collector unreachable; log warning only).
6. Add Docker Compose + Prometheus + Grafana provisioning.
7. Add Loki/Tempo/Collector config.
8. Finalize README and pre-commit.

---

## 16) Error Handling Policy (Strict)

- Never raise raw exceptions to clients.
- Always return JSON error envelope with stable `type`.
- For partial model failures:
  - keep `responses[i].error` populated
  - compute consensus using remaining successful responses
- If all models fail:
  - `winner = null`, `confidence = 0.0`, include errors.

---

## 17) Notes to the Agent (Avoid common mistakes)

- Do not duplicate contracts in multiple places. Pydantic contracts are the canonical schema.
- Do not add unnecessary abstractions (interfaces, DI containers) beyond minimal needs.
- Ensure async code is correct: use `asyncio.gather` and enforce E2E timeout with `wait_for`.
- Ensure Docker compose service names match config endpoints (`otel-collector:4318`, `app:8000`).
- Grafana provisioning paths must match container directories.
- Keep dashboards minimal; correctness over beauty.

---

## 18) Deliverables

At the end, ensure these files exist and are correct:
- `pyproject.toml`, `README.md`, `.env.example`
- `docker-compose.yml`
- `docker/prometheus/prometheus.yml`
- `docker/otel/otel-collector-config.yaml`
- `docker/grafana/provisioning/datasources/datasources.yaml`
- `docker/grafana/provisioning/dashboards/dashboards.yaml`
- `docker/grafana/dashboards/api_overview.json`
- All Python packages and tests as specified.

End of agent instructions.