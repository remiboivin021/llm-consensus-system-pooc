# Repository Guidelines (Python library only)

## Project Goal & Scope
- Goal: a deterministic Python library that produces a single consensus response from multiple LLM candidates, with scoring signals for downstream decisions.
- Current scope: library-only (no bundled HTTP API or CLI). Apps can embed `lcs` and wire their own FastAPI/CLI if needed.
- Why: reduce variance/hallucinations by consolidating provider outputs behind stable contracts and guardrails.

## Current Architecture
- Package path: `src/` (imports as `src.*`); published package name remains `lcs` even though import path is `src.*`; keep naming aligned when adding modules.
- Core modules:
  - `contracts`: Pydantic models for requests/responses/errors (single source of truth).
  - `adapters.orchestration`: orchestrator, timeouts, provider result building, provider guardrail enforcement, and policy timeouts.
  - `adapters.providers`: OpenRouter client (lazy preamble load, optional code-format preamble) and transport factory with overridable timeouts.
  - `core.consensus`: judges (ScorePreferred, MajorityVote), scoring adapters, similarity.
  - `core.scoring`: scoring engine and helpers.
  - `policy`: loader + enforcer (pre/post gating, allowed_models incl. string/CSV/wildcard, provider guardrails).
  - `adapters.observability`: logging, tracing, metrics helpers (apps must call configure_* themselves).
- Data flow (library): build `ConsensusRequest` → `Orchestrator.run` → provider calls → scoring (optional) → judge → gating/guardrails → `ConsensusResult` or `OrchestrationError`.

## Key Behaviors & Invariants
- Provider guardrails enforced: `require_at_least_n_success`, `max_failure_ratio`, `max_timeout_ratio`.
- Policy timeouts override settings for both e2e and provider timeouts.
- Allowed models: `*`, single string, or CSV allowed list (whitespace trimmed); duplicates blocked when required; min/max models enforced.
- Errors normalize via `ErrorEnvelope` → `LcsError` (`provider_error`, `timeout`, `config_error`, `internal_error`).
- Preamble load is lazy; missing scoring config surfaces as clear `RuntimeError`/config_error instead of import crash.

## ADR Discipline
- Before modifying any code or docs, read every file under `docs/governance/adr/` in the current workspace. Do not make changes until all ADRs are reviewed for context.

## Build, Test, Dev Commands
- Install deps: `poetry install` (Python 3.11).
- Lint: `ruff check .`
- Tests: `poetry run pytest tests -v`
- Coverage example: `poetry run pytest tests/ -v --cov=lcs --cov-report=xml --cov-report=html --cov-fail-under=80`

## Coding Style & Practices
- Prefer small, explicit modules; 4-space indentation; `snake_case`.
- Keep core logic pure; IO at edges. No new deps unless justified.
- Design by Contract and defensive programming: validate inputs early; apply timeouts; handle partial failures.
- Determinism/idempotency: same inputs → same consensus.
- Observability is first-class but opt-in: apps call configure_logging/tracing; metrics via Prometheus client helpers.

## Testing Guidelines
- Unit focus: consensus rules, scoring, policy gating, provider guardrails, timeouts, error mapping, observability helpers.
- Adapters use mocked HTTP (respx/httpx); no live OpenRouter calls.
- Add regression tests for policy overrides and edge ratios; keep async tests deterministic (avoid real sleeps).

## Commit & PR Guidelines
- Branch from `develop` using `feat/*`, `bug/*`, or `hotfix/*`.
- Commit format: `<type>(<scope>): <subject>` with WHY/WHAT in body (see `GIT.md`).
- PRs target `develop`; include summary, linked issues, note tests/docs updates; run lint/tests before review.

## Security & Config
- No secrets in repo; use `.env.example` template.
- Follow `SECURITY.md` for vulnerability reporting; keep logging/metrics free of secrets.
