# Feature: Add structured run-event callback hook

Decision: Accept (priority: very high)
Scores: Originality 3/10 | Complexity 2/10 | Utility 8/10 | Overall 8/10

CEO/PO View
- Why: Hosts need audit/logging without bundled storage; a callback preserves library-only scope while enabling compliance use cases.
- Business impact: Increases adoption in regulated environments and keeps LCS lightweight.

Scope guardrails
- Non-blocking wrapper with timeout; swallow exceptions and meter failures.
- Minimal, documented event schema with sanitized fields.

Risks & mitigations
- User callbacks could still block → enforce timeout and run in executor.
- Sensitive data leakage → clearly document included fields and defaults.

Definition of success
- Callback fires on success/failure paths without impacting latency budgets.

Next step
- Define event schema, add callback option to orchestrator/client, instrument failure metric.
