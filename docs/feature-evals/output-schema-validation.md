# Feature: Output schema validation + one-shot re-ask

Decision: Accept (priority: medium-high)
Scores: Originality 5/10 | Complexity 6/10 | Utility 7/10 | Overall 7/10

CEO/PO View
- Why: Raises structured-output reliability by validating and retrying once without altering core contracts.
- Business impact: Improves success rate for structured consumers (apps expecting JSON/forms) with bounded latency cost.

Scope guardrails
- Optional validator hook (Pydantic/guardrails) with max_reask=1; default-off.
- If validation fails, return gated result with clear reason; respect overall timeout budget.

Risks & mitigations
- Added latency → single retry cap and configuration docs.
- Schema drift → version schemas and include validation error reason codes.

Definition of success
- When enabled, schema violations trigger one retry; failures surface as gated results with metrics for validation_fail and reask count.

Next step
- Add validator interface, wire policy flag, budget retries against timeout, and build schema mismatch fixtures.
