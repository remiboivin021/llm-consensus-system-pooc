# Roadmap

This roadmap reflects the current scope for MVP, V1, and V2.

## MVP (priority: MVP)

- [ ] Consensus API contract
  - [ ] request schema
  - [ ] response schema
  - [ ] example payloads
- [ ] API error model (baseline)
  - [ ] error codes
  - [ ] error structure
- [ ] Consensus compute endpoint
  - [ ] handler logic
  - [ ] validation
  - [ ] error mapping
- [ ] Run logging (SQLite)
  - [ ] schema migration
  - [ ] write path
  - [ ] config flag
- [ ] Logging privacy policy
  - [ ] redact rules
  - [ ] fields to store
  - [ ] fields to exclude
- [ ] Stability signal (basic)
  - [ ] define signal
  - [ ] compute value
  - [ ] include in response
- [ ] Minimal benchmark harness
  - [ ] latency measurement
  - [ ] accuracy checks
  - [ ] hallucination checks
- [ ] Health probes
  - [ ] /health
  - [ ] /ready JSON status
- [ ] Metrics emission (basic)
  - [ ] count
  - [ ] latency
  - [ ] error
- [ ] Run model (basic)
  - [ ] identifiers
  - [ ] timestamps
  - [ ] storage mapping
- [ ] Request validation rules
  - [ ] size limits
  - [ ] required fields
  - [ ] error responses
- [ ] Local run workflow
  - [ ] Rust service run
  - [ ] Python execution run
  - [ ] integration steps
- [ ] Docs starter pack
  - [ ] usage
  - [ ] quickstart
  - [ ] sample request

## V1 (priority: V1)

- [ ] Versioned API surface
  - [ ] routing
  - [ ] compatibility
  - [ ] docs
- [ ] Auth decision
  - [ ] explicit stance (none or defined)
  - [ ] document rationale
- [ ] Scoring storage + lookup
  - [ ] schema
  - [ ] run lookup
  - [ ] filters
- [ ] Judge-based scoring
  - [ ] prompt template
  - [ ] rubric
  - [ ] async worker
- [ ] Regression gating
  - [ ] test suite
  - [ ] thresholds
  - [ ] CI integration
- [ ] Stability signal (advanced)
  - [ ] variance/confidence
  - [ ] calibration
  - [ ] QA
- [ ] Metrics endpoint
  - [ ] metrics
  - [ ] format
  - [ ] security
- [ ] Metrics format standard
  - [ ] schema
  - [ ] ownership
- [ ] Metrics emission (detailed)
  - [ ] per-model
  - [ ] per-endpoint
  - [ ] errors
- [ ] Scoring configuration
  - [ ] schema
  - [ ] validation
  - [ ] reload
- [ ] Error contract
  - [ ] codes
  - [ ] structure
  - [ ] examples
- [ ] Retention policy
  - [ ] config
  - [ ] purge
  - [ ] docs
- [ ] API documentation refresh
  - [ ] OpenAPI
  - [ ] examples
  - [ ] changelog

## V2 (priority: V2)

- [ ] Evidence + benchmarks
  - [ ] evidence mode design
  - [ ] benchmark strategy
  - [ ] reporting format
- [ ] Evidence mode endpoint
  - [ ] endpoint contract
  - [ ] evidence payload
  - [ ] response format
- [ ] Dataset benchmarks
  - [ ] dataset selection
  - [ ] benchmark runner
  - [ ] baseline metrics
- [ ] Long-term logging store
  - [ ] storage backend choice
  - [ ] retention tiers
  - [ ] export tooling
- [ ] Local NoSQL selection
  - [ ] database choice
  - [ ] rationale
- [ ] Provenance
  - [ ] data lineage fields
  - [ ] attribution capture
  - [ ] audit trail
- [ ] Drift metrics
  - [ ] drift definition
  - [ ] detection pipeline
  - [ ] alert thresholds
- [ ] Benchmark report
  - [ ] report template
  - [ ] automated generation
  - [ ] publish workflow
- [ ] Storage migration
  - [ ] migration plan
  - [ ] backfill job
  - [ ] validation checks
- [ ] Evidence schema
  - [ ] schema definition
  - [ ] validation rules
  - [ ] versioning

See the [open issues](https://github.com/remiboivin021/llm-consensus-system/issues) for a full list of proposed features (and known issues).

> **NOTE:** Sprint load distribution: week 1 ~80%, week 2 ~70%, week 3 ~40% of a 20h/week
