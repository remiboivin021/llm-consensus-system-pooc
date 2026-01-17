# Code View

This view summarizes the language-specific code views for LCS.

## Code View Context

Code views are language-specific because each service has its own module layout
and dependencies. The Rust and Python services define their code structure in
their respective C4 code views.

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
  classDef view fill:#EEF5FF,stroke:#2B6CB0,stroke-width:1px,color:#1F2937

  Root["LCS Code Views"]:::view
  Rust["Rust Code View<br/>(rust/docs/architecture/c4/code.md)"]:::view
  Python["Python Code View<br/>(python/docs/architecture/c4/code.md)"]:::view

  Root --> Rust
  Root --> Python
```

## Technical Context

See `rust/docs/architecture/c4/code.md` and `python/docs/architecture/c4/code.md`
for the service-specific module diagrams and notes.
