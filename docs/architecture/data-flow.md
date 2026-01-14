# Data Flow

## Overview

1. Client sends a consensus request to the API.
2. API validates input and forwards to the consensus core.
3. Core triggers LLM adapters to produce candidate responses.
4. Core computes consensus and scoring.
5. Metrics are emitted and optional logs are persisted.
6. API returns the final response.

## Notes

- Logging behavior depends on the release phase (MVP, V1, V2).
- Storage is optional for MVP and required for V1+.
