# C4 Container Diagram

## Containers

- API service (Rust)
- LLM execution service (Python)
- Optional storage (SQLite for MVP/V1)
- Optional long-term storage (WatermelonDB for V2)

## Relationships

- API service calls LLM execution service
- API service persists logs to storage when enabled
