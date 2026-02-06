# Feature: Add reliability-weighted judge

Decision: Accept (priority: medium-high)
Scores: Originality 6/10 | Complexity 6/10 | Utility 7/10 | Overall 7/10

CEO/PO View
- Why: Automatically down-weights flaky models, improving consensus robustness without user intervention.
- Business impact: Higher perceived reliability and lower incident volume when a model degrades.

Scope guardrails
- Sliding-window stats with TTL; weights clamped to [0,1].
- Deterministic ties and fallback to majority when data sparse.
- In-memory only; no new storage dependency.

Risks & mitigations
- Sparse data producing noisy weights → minimum sample threshold and decay.
- Divergent state across workers → document per-process behavior; later consider shared cache if needed.

Definition of success
- Deterministic output given same stats snapshot.
- Bench tests show improved accuracy/robustness on simulated failure bursts.

Next step
- Prototype judge with injected stats source and add regression tests for weighting and tie handling.
