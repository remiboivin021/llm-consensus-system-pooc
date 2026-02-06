# Module Structure

## Core

- Consensus logic
- Scoring and evaluation rules
- Domain models and interfaces

## Adapters

- API transport adapter
- Python LLM adapter (HTTP)
- Python LLM adapter (FFI, future)
- Storage adapters

## Shared

- Error types
- Metrics and logging primitives

## Repository Layout

```
src/   # language-agnostic specs/contracts
rust/  # Rust service implementation
python/ # Python LLM implementation
ffi/   # FFI bindings and build glue
```
