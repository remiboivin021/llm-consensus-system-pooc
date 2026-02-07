# Feature: Gate-reason telemetry & drift alerts

Decision: Accept (priority: medium)
Scores: Originality 3/10 | Complexity 2/10 | Utility 6/10 | Overall 6/10

CEO/PO View
- Why: Adds visibility into why gating happens, enabling proactive alerts on drift (e.g., prompt_too_long spikes).
- Business impact: Faster incident detection and tuning without heavy lift.

Scope guardrails
- Enumerated, low-cardinality reason codes; labeled Prometheus counter.
- Optional moving-average helper; no persistence.

Risks & mitigations
- Cardinality creep → cap reasons and reject unknowns.
- Alert fatigue → provide suggested alert thresholds and smoothing.

Definition of success
- Metrics emit counts by reason in shadow/soft modes; dashboards/alerts can track shifts.

Next step
- Define reason enum, expose counter, add tests for emission paths.
