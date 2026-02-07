# Feature: Timeout tuner helper (offline)

Decision: Accept (priority: medium)
Scores: Originality 4/10 | Complexity 4/10 | Utility 6/10 | Overall 6/10

CEO/PO View
- Why: Offline tool suggests provider/e2e timeouts from observed latency percentiles, improving reliability without runtime risk.
- Business impact: Helps teams set sane defaults, reducing timeouts/errors in production.

Scope guardrails
- Read-only util ingesting metrics CSV/JSON; deterministic suggestions with min/max clamps.
- No network or runtime dependencies.

Risks & mitigations
- Poor input data leads to bad advice → warn on insufficient samples and display assumptions.
- Misuse as authoritative → clearly mark outputs as suggestions.

Definition of success
- Given sample latency data, tool emits a policy snippet with bounded, reproducible timeout values.

Next step
- Build helper script, add fixture-driven tests, document workflow.
