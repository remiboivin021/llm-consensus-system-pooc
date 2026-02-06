# Deployment Architecture

## Environments

- Local development
- Staging (optional)
- Production

## Services

- LCS API service (Rust)
- LLM execution service (Python)
- Optional storage service for run logs

## Deployment Goals

- Stateless API where possible
- Clear separation between core and adapters
- Observability enabled by default
