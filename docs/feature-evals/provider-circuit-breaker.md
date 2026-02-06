# Feature: Provider circuit-breaker with backoff

Decision: Accept (priority: high)
Scores: Originality 5/10 | Complexity 6/10 | Utility 8/10 | Overall 8/10

CEO/PO View
- Why: Shields users from provider outages by short-circuiting quickly and recovering gracefully.
- Business impact: Improves uptime and user trust; reduces noisy incidents when upstream degrades.

Scope guardrails
- In-memory breaker per model with decay thresholds; respects policy failure/timeout ratios.
- Observable state for debugging; never blocks successful calls.

Risks & mitigations
- Over-aggressive trips → tune thresholds and include hysteresis.
- Divergent breaker state across workers → document process-local behavior; future shared store optional.

Definition of success
- Failure bursts trigger breaker open/close metrics; successful calls still pass.
- Latency/timeout spikes show reduced wasted attempts in load tests.

Next step
- Implement breaker with decay/backoff, integrate into orchestration flow, add simulated failure tests.
