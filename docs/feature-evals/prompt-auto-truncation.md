# Feature: Prompt auto-truncation with provenance note

Decision: Accept (priority: medium)
Scores: Originality 3/10 | Complexity 2/10 | Utility 6/10 | Overall 6/10

CEO/PO View
- Why: Avoids hard failures on overlength prompts by truncating deterministically and surfacing provenance metadata.
- Business impact: Reduces support load for length errors while staying transparent and opt-in.

Scope guardrails
- Policy flag to enable; deterministic middle-ellipsis; records bytes removed and note in result.
- Still respects gating if strict block configured.

Risks & mitigations
- Information loss harming output quality → keep opt-in and document trade-offs.
- Unicode/byte edge cases → add boundary tests for multibyte chars.

Definition of success
- When enabled, too-long prompts are truncated, noted in metadata, and never exceed configured max; when disabled, current blocking behavior remains.

Next step
- Implement truncation helper, wire policy toggle, add boundary tests.
