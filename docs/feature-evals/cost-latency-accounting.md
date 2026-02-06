# Feature: Optional cost/latency accounting

Decision: Accept (priority: medium)
Scores: Originality 3/10 | Complexity 3/10 | Utility 6/10 | Overall 6/10

CEO/PO View
- Why: Lets users reason about price/speed trade-offs without billing integration; keeps LCS as decision aid.
- Business impact: Supports procurement and SRE teams choosing models; modest differentiation.

Scope guardrails
- Optional pricing hints per model; defaults to zero.
- Deterministic accumulation into metadata; no external billing calls.

Risks & mitigations
- Stale prices misleading users → version config and document approximation limits.
- Misinterpretation as authoritative billing → clearly label as estimates.

Definition of success
- When hints supplied, results include cost/latency summary; absent hints leave zeros without errors.

Next step
- Extend ModelResponse metadata, add tests for presence/absence of pricing config, document approximation caveats.
