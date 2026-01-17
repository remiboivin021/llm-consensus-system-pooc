# Architecture ()

This file captures the architecture of LCS. It is intentionally self-contained and references supporting diagrams where relevant.

## Introduction and Goals

LCS provides consensus over multiple LLM outputs through a REST/JSON API. The primary goal is to deliver a single consolidated response along with evaluation signals such as score, consensus confidence, and hallucination rate. The system is designed to be embedded into other software workflows rather than bundled as
an end-user application.

## Architecture Constraints

LCS is implemented with Rust for orchestration and security-sensitive logic and
Python for LLM execution. MVP and V1 expose REST/JSON only. Each request is stateless and includes its own prompt and context. Clean/hexagonal architecture is enforced to keep core logic independent from infrastructure. Authentication and rate limiting are handled by an external service positioned in front of LCS.

OpenRouter is the current external LLM provider. No web search is used in MVP/V1.

## Context and Scope

The system context, actors, and external systems are documented in the context view diagram at `docs/architecture/c4/context.md`. The scope includes consensus logic, its REST/JSON interface, and the LLM provider integration. Training, UI, billing, user management, and in-process rate limiting are out of scope.
Prompt/context persistence is not part of MVP. V1 logging is limited and does not introduce cross-request memory. V2 can enable offline persistence in a NoSQL store for system improvement.

## Solution Strategy

The solution strategy is to isolate the consensus core from transport and infrastructure concerns. Ports define contracts for external dependencies and adapters implement those contracts. This allows LCS to use an HTTP-based Python LLM adapter in MVP/V1 while keeping the door open for an FFI adapter in V2 without changing core logic.

## Building Block View

The system is structured around a core domain, application services, ports, and adapters. Inbound adapters handle REST/JSON requests and map them to use cases.
Outbound adapters include the Python LLM adapter, storage adapters for logging,
and metrics/logging emitters. The repository layout aligns with this split:

- `src/` for shared contracts
- `rust/` for the service
- `python/` for LLM execution
- `ffi/` for future bindings

## Runtime View

A client sends a REST/JSON request containing prompt and context. The external Auth/Rate-Limit service validates the request before forwarding it to LCS. The LCS API validates the input, invokes the consensus core, and calls the external LLM provider to obtain candidate responses. The core computes consensus and
scores, emits metrics, logs the run (optional in MVP, required in V1+), and returns the final response with evaluation signals.

## Deployment View

LCS runs as a standalone service. The Rust API service hosts the consensus core and communicates with a Python LLM execution component. Storage is optional in MVP and uses SQLite when enabled. V1 requires SQLite for run logging. V2 introduces a local NoSQL option for long-term logging and system improvement. Auth and rate limiting are external services in front of LCS.

## Crosscutting Concepts

Errors are explicit and mapped to a defined error model. Observability includes
latency and error metrics, with logging policy defined per release phase. Input
validation is enforced at the API boundary. Security controls focus on reducing
attack surface and avoiding logging of sensitive data by default.

## Architectural Decisions

Architectural decisions are captured as ADRs in `docs/governance/adr/`. No
architecture decisions are finalized beyond the constraints listed above.

## Quality Requirements

Quality goals are not yet formalized and will be defined as the MVP stabilizes.

## Risks and Technical Debt

Risks and technical debt have not been formalized yet and will be tracked when
implementation begins.

## Glossary

Terminology is defined in `docs/references/glossary.md`.
