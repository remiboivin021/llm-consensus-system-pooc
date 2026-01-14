# Monitoring Tooling

Monitoring backend is not selected yet. This document defines the logging
policy per release phase.

## Logging Policy

- MVP: minimal metrics only, stored in SQLite.
- V1: metrics, config, results, and partial traces in SQLite.
- V2: full logs, datasets, benchmarks, and provenance in WatermelonDB or an
  equivalent long-term store.
