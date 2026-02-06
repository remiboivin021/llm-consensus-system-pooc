# C4 — Code

This code-level view maps the main modules, interfaces, and safeguards so contributors can navigate and extend LCS confidently.

Package layout: the public API sits in `src/__init__.py` and `src/client.py`, exposing `LcsClient`, `consensus`, and `list_strategies`. Contracts live under `src/contracts` (`ConsensusRequest`, `ConsensusResult`, `ModelResponse`, `ErrorEnvelope`). Settings are defined in `src/config.py` using Pydantic; defaults include three free OpenRouter models and conservative timeouts. Policy definitions are in `src/policy/models.py` with the loader and enforcer in the same package.

Consensus mechanics: `src/core/analysis/embeddings.py` produces deterministic bag-of-words embeddings and `similarity.py` computes cosine similarity. `src/core/consensus/voting.py` ranks responses by average similarity, while `src/core/consensus/scoring.py` aggregates quality scores. `src/core/consensus/strategies.py` chooses between scoring-first and vote-first flows, and `registry.py` keeps the strategy map. Confidence is calculated by relative score gaps and clamped to `[0,1]`.

Scoring details: `src/core/scoring/engine.py` extracts code from JSON or fenced blocks, parses it with `ast`, and evaluates metrics using radon (complexity/MI), pycodestyle, pydocstyle, vulture, and bandit when available. Missing optional dependencies default to neutral scores instead of failing. Weights are explicit in `WEIGHTS`; overall scores are clamped and aggregated into `ScoreDetail` plus `ScoreStats`.

Orchestration and providers: `src/adapters/orchestration/orchestrator.py` enforces prompt length, model count, and **policy overrides for both e2e and provider timeouts** before dispatching concurrent provider calls through `fetch_provider_result`. Provider guardrails (`require_at_least_n_success`, `max_failure_ratio`, `max_timeout_ratio`) are enforced immediately after responses are built, gating before scoring/judging. Each provider response is wrapped as `ProviderResult` and converted to `ModelResponse`. OpenRouter integration in `src/adapters/providers/openrouter.py` uses lazy preamble loading (`get_python_code_format_preamble`) so missing files fail fast with a clear config error; transport timeouts are overridable per call via `get_client(timeout_ms=...)`. System preambles: `STRUCTURED_PREAMBLE` for normalized output and `PYTHON_CODE_FORMAT_PREAMBLE` (lazy attribute) for code-scoring prompts. HTTP transport configuration lives in `src/adapters/providers/transport.py`.

Error handling: provider failures produce `ErrorEnvelope` per model; orchestrator-level issues raise `OrchestrationError` carrying an envelope, which `LcsClient` converts to `LcsError` with stable codes (`provider_error`, `timeout`, `config_error`, `internal_error`). Gating may mark a result as `gated=True` with `gate_reason` without raising, keeping soft failures visible to callers.

Observability and testing: metrics, logging, and tracing live under `src/adapters/observability`. Tests use pytest with asyncio support (`tests/unit/test_orchestrator.py`, `test_orchestration_fetch_preamble.py`, `test_scoring.py`, `test_transport.py`). Mutation testing is configured via Mutmut. Run `poetry run pytest -q` for the suite, `poetry run ruff check .` for lint, and `poetry run black --check .` for formatting before committing changes.

---
Maintainer/Author: Rémi Boivin (@remiboivin021)
Version: 0.1.0
Last modified: 2026-02-03
---
