# API Overview

The LCS API is REST/JSON for MVP and V1. This document lists the core endpoints
and usage modes.

## Endpoints

- `POST /consensus`: compute a consensus response
- `POST /consensus/evidence`: compute consensus with evidence (V2 mode)
- `GET /health`: service health check
- `GET /metrics`: metrics endpoint
- `GET /runs/{id}`: retrieve a logged run (when logging is enabled)

## Authentication and Authorization

Authentication and authorization are not defined for MVP. See the dedicated
documents once requirements are finalized.

## Error Handling

See `error_codes.md` once the error schema is defined.

## Versioning

See `versioning.md` for versioning policy.
