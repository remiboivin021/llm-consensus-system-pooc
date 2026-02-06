# Monitoring Tooling

Monitoring backend is not selected yet. This document defines the logging
policy per release phase.

## Logging Policy

- MVP: minimal metrics only; if logging is enabled, store in SQLite.
- V1: required logging of metrics, config, results, and partial traces in SQLite.
- V2: full logs, datasets, benchmarks, and provenance in a NoSQL store (TBD) to
  support system improvement.
