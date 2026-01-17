# Component View

This view decomposes the Rust API service into layers. It shows how interface
components call application logic, which relies on domain rules and
infrastructure adapters.

## Component Context

This component view focuses on the Rust API service that owns consensus and
scoring. It clarifies which responsibilities live inside the service boundary
and which ones are delegated to external systems. The intent is to explain
ownership and coupling rather than restate every connection in the diagram.

LCS is request driven and stateless in MVP and V1. Each request is handled as a
single unit of work and returns a single response payload. There is no
cross-request memory, and persistence is limited to run logging and offline
analysis. Logging is optional in MVP and required in V1+.

The entry path starts with a client calling the external Auth/Rate-Limit
service, which then forwards the request to the REST API. The dotted arrows
represent the end-to-end response path back to the client and are conceptual
rather than a timing diagram. Domain returns are implicit to keep the diagram
readable, since those calls are in-process and do not cross boundaries.

External dependencies are shown to expose operational boundaries. The Python
LLM execution service is the only component that communicates with providers.
SQLite is used for run logging in MVP and V1; it is optional in MVP and
required in V1+. Metrics and tracing systems are external and treated as
best-effort destinations.

### Diagram (Mermaid)

```mermaid
---
config:
  flowchart:
    nodeSpacing: 90
    rankSpacing: 130
    curve: linear
  layout: elk
---
flowchart TB
  classDef iface fill:#EEF5FF,stroke:#2B6CB0,stroke-width:1px,color:#1F2937
  classDef app fill:#ECFDF5,stroke:#0F766E,stroke-width:1px,color:#1F2937
  classDef domain fill:#FFF7ED,stroke:#C2410C,stroke-width:1px,color:#1F2937
  classDef infra fill:#F3F4F6,stroke:#4B5563,stroke-width:1px,color:#1F2937
  classDef external fill:#FFF5F5,stroke:#C53030,stroke-width:1px,color:#7F1D1D
  classDef database fill:#F0F9FF,stroke:#0284C7,stroke-width:1px,color:#1F2937

  subgraph Entry[" "]
    direction TB
    Client["Client (Human or External System)"]:::external
    Auth["Auth/Rate-Limit Service<br/>(external)"]:::external
  end
  style Entry fill:transparent,stroke:transparent

  subgraph LcsRust["LCS API Service (Rust)"]
    direction TB

    subgraph Iface["Interfaces"]
      direction LR
      RestApi["REST API"]:::iface
    end

    subgraph App["Application"]
      direction LR
      Validation["Request Validation"]:::app
      Orchestrator["Consensus Orchestrator"]:::app
      Scoring["Scoring Engine"]:::app
    end

    subgraph Domain["Domain"]
      direction LR
      ConsensusRules["Consensus Rules"]:::domain
      ScoringRules["Scoring Rules"]:::domain
      RunModel["Run Model"]:::domain
    end

    subgraph Infra["Infrastructure"]
      direction LR
      LlmAdapter["LLM Adapter (HTTP)"]:::infra
      StoreAdapter["Run Store Adapter<br/>(SQLite, MVP optional)"]:::infra
      MetricsAdapter["Metrics Adapter"]:::infra
    end
  end

  PyLLM["LLM Execution Service<br/>(Python)"]:::external
  SQLite[("SQLite<br/>(MVP optional)")]:::database
  MetricsExt["Metrics/Tracing System<br/>(external)"]:::external

  Client -->|request| Auth
  Auth -->|REST/JSON| RestApi
  RestApi -->|validate request| Validation
  Validation -->|dispatch| Orchestrator
  Orchestrator -->|score| Scoring
  Scoring -->|apply rules| ScoringRules
  Orchestrator -->|apply rules| ConsensusRules
  Orchestrator -->|build run| RunModel
  Orchestrator -->|request candidates| LlmAdapter
  Orchestrator -->|persist run| StoreAdapter
  Orchestrator -->|emit metrics| MetricsAdapter

  LlmAdapter -->|HTTP| PyLLM
  StoreAdapter -->|write| SQLite
  MetricsAdapter -->|metrics/traces| MetricsExt

  PyLLM -.->|response| LlmAdapter
  LlmAdapter -.-> Orchestrator
  Orchestrator -.-> RestApi
  RestApi -.->|response| Auth
  Auth -.->|response| Client

  linkStyle default stroke:#1F4E79,stroke-width:2.5px
  linkStyle 14,15,16,17,18 stroke:#64748B,stroke-width:2.5px
```

## Technical Context

The Rust API service follows a strict hexagonal layering model. Interfaces handle transport concerns, the application layer coordinates workflows, the domain layer expresses rules and invariants, and infrastructure hosts adapters for IO and external systems. Dependencies always point inward toward the domain, and adapters implement ports defined by the core.

The REST API interface owns decoding, schema validation, and response shaping.
It protects the core from HTTP and serialization details while exposing a stable public contract. This layer rejects malformed inputs early and forwards normalized requests into application logic.

The application layer coordinates consensus and scoring. It handles request validation, enforces limits and timeouts, and decides how to proceed when candidate data is incomplete. The orchestrator uses the execution port to retrieve candidates and then applies scoring according to domain rules.

The scoring engine remains internal because it is part of the core business logic. Scores are deterministic for a given input and are attached to the response as metadata. The scoring path does not call external systems and does not persist state across requests.

Domain logic defines what a valid consensus outcome means. The domain layer is pure and side-effect free, with explicit types and errors. It does not depend on HTTP, storage, or telemetry and is the main source of truth for consensus and
scoring behavior.

Infrastructure adapters isolate IO and provider details. The LLM adapter translates internal requests into provider calls and maps responses into candidate structures. The store adapter is optional in MVP and required in V1+ for
logging and evaluation, while the metrics adapter emits telemetry without influencing business decisions.

Error handling is explicit across all layers. Validation errors are returned to clients as stable error responses, and provider failures can trigger a degraded mode with partial results. Diagnostics are emitted without blocking request completion, and errors never silently alter the consensus logic.

The system is stateless and designed for horizontal scaling. Timeouts and request budgets prevent unbounded execution, and logging storage remains off the critical path. Performance and reliability are managed through orchestration policy rather than through hidden background work.

Security and access control are delegated to the gateway. The service assumes requests arriving at the REST API have already passed authentication and rate limits. Sensitive data is minimized in logs and metrics, and provider credentials are managed outside the core.

The component view is expected to remain stable as adapters evolve. New providers can be added by implementing new adapters, and storage backends can be replaced without changing domain rules. The same boundaries can support future FFI execution paths or additional tooling as the system matures.
