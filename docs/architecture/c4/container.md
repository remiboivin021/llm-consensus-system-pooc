# Container View

This view decomposes LCS into deployable units and external dependencies. It
captures runtime boundaries that are relevant to operation and scaling.

## Container View Context

The Rust API service hosts the consensus core and exposes the REST/JSON API.
The Python LLM service encapsulates provider-specific logic and communicates
with OpenRouter. Authentication and rate limiting are enforced by an external
service positioned in front of LCS.

SQLite is optional in MVP and required in V1+ for run logging. No other runtime
data stores are required for MVP/V1.

### Diagram (PlantUML)

```plantuml
@startuml
top to bottom direction

actor "Human User" as Human
actor "External Client System" as Client

rectangle "Auth/Rate-Limit Service\n(external)" as Auth
rectangle "LCS API Service\n(Rust)" as RustAPI
rectangle "LLM Execution Service\n(Python)" as PyLLM
rectangle "OpenRouter\n(LLM Provider)" as OpenRouter
rectangle "SQLite\n(MVP optional)" as SQLite

Human --> Auth : REST/JSON\nprompt + context
Client --> Auth : REST/JSON\nprompt + context
Auth --> RustAPI : REST/JSON\nrequest
RustAPI --> PyLLM : HTTP\nLLM request
PyLLM --> OpenRouter : provider API\ncandidates

RustAPI ..> SQLite : log run (MVP optional)
RustAPI --> Human : response + score +\nconsensus_confidence +\nhallucination_rate
RustAPI --> Client : response + score +\nconsensus_confidence +\nhallucination_rate
@enduml
```

## Technical Context

The Python LLM service is the only component that communicates with OpenRouter.
This keeps provider-specific concerns isolated from the Rust consensus core.

The external Auth/Rate-Limit service is required for access control and is not
implemented inside LCS. Requests reaching LCS are assumed to have already passed
those controls.

Persistence is limited to logging and evaluation. V1+ logging does not provide
cross-request state or memory for runtime consensus behavior. V2 uses a NoSQL
store for long-term logging and system improvement.
