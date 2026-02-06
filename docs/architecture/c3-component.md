# C3 — Component

This component view breaks down the LCS library into its major parts and shows how a request flows through them.

Entry points and contracts: `src.client` exposes `LcsClient.run` and helper `consensus`; `src.contracts.request` and `src.contracts.response` define the Pydantic payloads exchanged internally and with hosts. Configuration is supplied by `src.config.Settings`, while `src.errors` converts internal envelopes into `LcsError` for callers.

Core logic: `src.core.consensus` hosts judges such as `MajorityVoteJudge`, `ScoreAggregationJudge`, and the `ScorePreferredJudge` strategy selector. Similarity utilities live in `src.core.analysis` (hash-based embeddings and cosine similarity). Quality scoring resides in `src.core.scoring.engine`, which extracts code from responses and computes metrics for performance, complexity, tests, style, documentation, dead code, and security.

Orchestration: `src.adapters.orchestration.orchestrator` coordinates the end-to-end flow. It loads policy via `src.policy.loader`, applies preflight gating, spawns concurrent provider calls through `src.adapters.orchestration.models.fetch_provider_result`, applies timeouts from `src.adapters.orchestration.timeouts`, computes scores when requested, and invokes the chosen judge. Post-flight gating is handled by `src.policy.enforcer`, which can annotate or gate the result.

Provider integration: `src.adapters.providers.openrouter` builds chat completion requests to OpenRouter using httpx transport from `src.adapters.providers.transport`. It supports optional system preambles for structured outputs and code-scoring scenarios.

Observability: `src.adapters.observability.metrics` defines Prometheus counters, histograms, and gauges. `src.adapters.observability.logging` sets up structlog and optional OTLP log export. `src.adapters.observability.tracing` instruments a FastAPI host and httpx client when provided, enabling spans around consensus scoring.

A typical request enters through `LcsClient`, is validated via the contracts, filtered by policy, executed concurrently against OpenRouter, scored if requested, judged for consensus, optionally gated, and finally returned as `ConsensusResult`. Errors are wrapped in `ErrorEnvelope` per model and collapsed into `LcsError` when they reach the caller.

Validate component behaviour with `poetry run pytest tests/unit/test_orchestrator.py tests/unit/test_policy_enforcer.py tests/unit/test_voting_and_scoring.py tests/unit/test_consensus.py`, which exercise gating, concurrency, similarity voting, and scoring.

---
Maintainer/Author: Rémi Boivin (@remiboivin021)
Version: 0.1.0
Last modified: 2026-02-03
---
