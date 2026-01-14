# Interfaces

## API Interface

- REST JSON API
- Endpoints: `POST /consensus`, `POST /consensus/evidence`, `GET /health`,
  `GET /metrics`, `GET /runs/{id}`

## Core Ports

- LLM provider port
- Scoring/metrics port
- Storage port (optional)

## Adapter Types

- HTTP adapter for API
- Python adapter for LLM execution
- SQLite adapter for run logging
- Long-term storage adapter for V2
