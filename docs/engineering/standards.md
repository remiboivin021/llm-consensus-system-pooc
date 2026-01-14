# Engineering Standards

These standards apply to all contributions to LCS.

## Architecture

- Use clean/hexagonal architecture.
- Core domain logic must not depend on transport, storage, or external services.
- Adapters isolate infrastructure concerns from the core.

## Rust

- Keep modules small and cohesive.
- Avoid `unsafe` unless explicitly justified.
- Use `clippy` and `rustfmt`.

## Python

- Keep modules small and cohesive.
- Avoid hidden side effects.
- Use explicit error handling.

## Error Handling

- No silent failures.
- Errors must be surfaced with context.
- Define error categories for observability.

## Observability

- Key metrics must be emitted for latency and consensus behavior.
- Logging must follow the versioned logging policy.
