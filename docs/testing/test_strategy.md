# Test Strategy

## Goals

- Validate consensus correctness
- Measure latency and reliability
- Detect regressions

## Levels

- Unit tests for core logic
- Integration tests for API and adapters
- Performance tests for latency and throughput
- Security tests for API boundaries

## Version Alignment

- MVP: focus on unit and basic integration tests
- V1: add LLM-as-judge evaluation tests
- V2: add dataset-based benchmarks

## Stability Gates

- MVP: agreement rate and human review cadence are primary indicators.
- V1: regression suite is the primary gate once available; other indicators are
  supporting signals.
- V2: add online variance and drift metrics as supporting signals.
