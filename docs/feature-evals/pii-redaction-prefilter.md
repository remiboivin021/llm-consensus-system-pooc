# Feature: Optional PII redaction prefilter

Decision: Accept (priority: high)
Scores: Originality 4/10 | Complexity 5/10 | Utility 8/10 | Overall 7/10

CEO/PO View
- Why: Masks sensitive data before provider calls, unlocking regulated workloads without bundling storage or changing core flow.
- Business impact: Expands addressable market (compliance-heavy teams) with contained effort and optional dependency.

Scope guardrails
- Optional module with policy flag; deterministic masking; audit-friendly redaction map.
- Default-off; no impact when unused.

Risks & mitigations
- Over-redaction harming output quality → confidence thresholds and preview mode.
- Dependency footprint → keep as extra and document version pinning.

Definition of success
- When enabled, prompts are masked deterministically; redaction metadata returned; metrics count redactions.

Next step
- Integrate redactor hook, emit redaction map, add PII fixtures and idempotence tests.
