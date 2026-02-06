# Roadmap

This roadmap reflects the current scope for MVP, V1, V2, and V3.

## MVP (priority: MVP)

- [ ] Define the consensus API contract.
  - [ ] Define the request schema.
  - [ ] Define the response schema.
  - [ ] Provide example payloads.
- [ ] Define a baseline API error model.
  - [ ] Define error codes.
  - [ ] Define error structure.
- [ ] Implement the consensus compute endpoint.
  - [ ] Implement handler logic.
  - [ ] Validate inputs.
  - [ ] Map errors to the error model.
- [ ] Implement run logging in SQLite.
  - [ ] Create the schema migration.
  - [ ] Implement the write path.
  - [ ] Add a config flag for logging.
- [ ] Define a logging privacy policy.
  - [ ] Define redaction rules.
  - [ ] Define fields to store.
  - [ ] Define fields to exclude.
- [ ] Define a basic stability signal.
  - [ ] Define the signal.
  - [ ] Compute the signal value.
  - [ ] Include it in responses.
- [ ] Build a minimal benchmark harness.
  - [ ] Measure latency.
  - [ ] Add accuracy checks.
  - [ ] Add hallucination checks.
- [ ] Add health probes.
  - [ ] Implement /health.
  - [ ] Implement /ready JSON status.
- [ ] Emit basic metrics.
  - [ ] Count requests.
  - [ ] Measure latency.
  - [ ] Count errors.
- [ ] Define the basic run model.
  - [ ] Define identifiers.
  - [ ] Define timestamps.
  - [ ] Define storage mapping.
- [ ] Define request validation rules.
  - [ ] Set size limits.
  - [ ] Define required fields.
  - [ ] Define error responses.
- [ ] Document a local run workflow.
  - [ ] Describe how to run the Rust service.
  - [ ] Describe how to run the Python execution service.
  - [ ] Describe integration steps.
- [ ] Produce a docs starter pack.
  - [ ] Add usage.
  - [ ] Add quickstart.
  - [ ] Add a sample request.

## V1 (priority: V1)

- [ ] Add rate limiting.
- [ ] Define a versioned API surface.
  - [ ] Implement routing.
  - [ ] Define compatibility rules.
  - [ ] Document the versioned API.
- [ ] Make an auth decision.
  - [ ] State the stance (none or defined).
  - [ ] Document the rationale.
- [ ] Implement scoring storage and lookup.
  - [ ] Define the schema.
  - [ ] Implement run lookup.
  - [ ] Implement filters.
- [ ] Implement judge-based scoring.
  - [ ] Define the prompt template.
  - [ ] Define the rubric.
  - [ ] Implement the async worker.
- [ ] Implement regression gating.
  - [ ] Define the test suite.
  - [ ] Define thresholds.
  - [ ] Integrate with CI.
- [ ] Implement an advanced stability signal.
  - [ ] Add variance/confidence.
  - [ ] Add calibration.
  - [ ] Add QA checks.
- [ ] Provide a metrics endpoint.
  - [ ] Define metrics.
  - [ ] Define output format.
  - [ ] Define security stance.
- [ ] Define a metrics format standard.
  - [ ] Define the schema.
  - [ ] Define ownership.
- [ ] Emit detailed metrics.
  - [ ] Emit per-model metrics.
  - [ ] Emit per-endpoint metrics.
  - [ ] Emit error metrics.
- [ ] Implement scoring configuration.
  - [ ] Define the schema.
  - [ ] Validate configuration.
  - [ ] Implement reload.
- [ ] Define the error contract.
  - [ ] Define codes.
  - [ ] Define structure.
  - [ ] Provide examples.
- [ ] Implement a retention policy.
  - [ ] Add config.
  - [ ] Implement purge.
  - [ ] Document the policy.
- [ ] Refresh API documentation.
  - [ ] Add OpenAPI.
  - [ ] Add examples.
  - [ ] Add changelog.

## V2 (priority: V2)

- [ ] Define evidence mode and benchmarks.
  - [ ] Define the evidence mode design.
  - [ ] Define the benchmark strategy.
  - [ ] Define the reporting format.
- [ ] Implement the evidence mode endpoint.
  - [ ] Define the endpoint contract.
  - [ ] Define the evidence payload.
  - [ ] Define the response format.
- [ ] Implement dataset benchmarks.
  - [ ] Select datasets.
  - [ ] Build the benchmark runner.
  - [ ] Define baseline metrics.
- [ ] Implement long-term logging storage.
  - [ ] Choose the storage backend.
  - [ ] Define retention tiers.
  - [ ] Build export tooling.
- [ ] Select a local NoSQL database.
  - [ ] Choose the database.
  - [ ] Document the rationale.
- [ ] Implement provenance tracking.
  - [ ] Define data lineage fields.
  - [ ] Capture attribution.
  - [ ] Maintain an audit trail.
- [ ] Implement drift metrics.
  - [ ] Define drift.
  - [ ] Build the detection pipeline.
  - [ ] Define alert thresholds.
- [ ] Build benchmark reporting.
  - [ ] Define the report template.
  - [ ] Automate generation.
  - [ ] Define the publish workflow.
- [ ] Implement storage migration.
  - [ ] Define the migration plan.
  - [ ] Build the backfill job.
  - [ ] Add validation checks.
- [ ] Define the evidence schema.
  - [ ] Define the schema.
  - [ ] Define validation rules.
  - [ ] Define versioning.

## V3 (priority: V3)

- [ ] Add optional MCP tool access.

See the [open issues](https://github.com/remiboivin021/llm-consensus-system/issues) for a full list of proposed features (and known issues).

> **NOTE:** Sprint load distribution: week 1 ~80%, week 2 ~70%, week 3 ~40% of a 20h/week
