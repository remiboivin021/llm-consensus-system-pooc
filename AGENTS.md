# Repository Guidelines

## Project Goal & Origin
- Goal: provide a service that computes a single consensus response from multiple LLM candidates, with scoring signals for downstream decisions.
- Why we started: LLM outputs vary and can hallucinate; we needed a deterministic, testable consensus layer that reduces variance and keeps provider-specific logic isolated.

## Project Structure & Module Organization
- `rust/` houses the Rust orchestration service; `python/` holds the LLM execution layer; `ffi/` will carry bindings/glue when added; `src/` keeps language-agnostic contracts/specs referenced in `docs/architecture/module_structure.md`.
- `docs/` is the canonical source for API, architecture, testing, and governance; module-specific conventions live in `rust/docs/` and `python/docs/`.
- Reference `DEV.md` for setup expectations and `CONTRIBUTING.md`/`GIT.md` for workflow rules before opening PRs.

## Architecture Context & Views (C4)
- Context: LCS sits behind an external Auth/Rate-Limit service, accepts REST/JSON requests, calls OpenRouter for candidates, and returns response + scoring signals (`docs/architecture/c4/context.md`).
- Container: deployable units are the Rust API service and the Python LLM execution service; optional SQLite is for logging only (`docs/architecture/c4/container.md`).
- Components: Rust API layers (REST API, validation, orchestrator, scoring, domain rules, adapters) live in `rust/docs/architecture/c4/component.md`.
- Components: Python execution layers (HTTP handler, orchestrator, prompt formatter, provider router, normalizer, contracts, provider client) live in `python/docs/architecture/c4/component.md`.

## Build, Test, and Development Commands
- Rust: `cargo fmt` (format), `cargo clippy --all-targets --all-features` (lint), `cargo test` (unit/integration), `cargo build` (verify compile).
- Python (3.11, `uv` for deps): `uv sync` or `uv pip install -r requirements.txt` when dependencies exist, `ruff check .` (lint/format), `pytest` (tests).
- CI mirrors these checks; make sure they pass locally to avoid churn.

## Coding Style & Naming Conventions
- Follow clean/hexagonal layering: keep core domain independent of adapters; avoid `unsafe` in Rust and hidden side effects in Python.
- Formatting is enforced by `rustfmt` (Rust) and `ruff` (Python); prefer 4-space indentation and `snake_case` file/function names.
- Keep modules small and cohesive; document non-obvious logic inline.

## Engineering Principles & Good Practices
- KISS: prefer simple, explicit designs over cleverness.
- YAGNI: avoid speculative features or flags.
- TDD for consensus/scoring rules and regressions; add tests before refactors.
- Defensive programming: validate inputs early, handle provider failures gracefully.
- Design by Contract (DbC): enforce pre/post conditions with types, validation, and invariants.
- SOLID: keep responsibilities focused and depend on stable abstractions/ports.
- Separation of concerns: keep IO at the edges and domain logic pure.
- Determinism/idempotency: same inputs should produce the same consensus output.

## Testing Guidelines
- Strategy is defined in `docs/testing/`: prioritize unit coverage of consensus rules, then adapter/API integration; add performance/security cases as features land.
- Place Rust tests alongside modules or in `tests/`; Python tests live under `tests/` with pytest-style names like `test_consensus.py::test_scoring_rule`.
- Coverage targets are still TBD; aim for meaningful assertions and include latency/metrics checks when relevant.

## Commit & Pull Request Guidelines
- Branch from `develop` using `feat/*`, `bug/*`, or `hotfix/*` prefixes.
- Commit format: `<type>(<scope>): <subject>` plus WHY/WHAT sections (see `GIT.md` examples); avoid generic subjects.
- PRs target `develop`, include a brief summary, link related issues, confirm docs/tests updates, and run the lint/test commands above before requesting review.

## Security & Configuration Tips
- Never commit secrets; use `.env.exemple` as a template and keep `.env` local.
- Report vulnerabilities privately per `SECURITY.md`; audit logging and threat model live under `docs/security/`.
