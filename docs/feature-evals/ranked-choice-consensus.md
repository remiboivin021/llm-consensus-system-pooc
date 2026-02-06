# Feature: Offer ranked-choice consensus mode

Decision: Defer (priority: medium)
Scores: Originality 5/10 | Complexity 5/10 | Utility 6/10 | Overall 6/10

CEO/PO View
- Why: Alternate voting (IRV/Borda) may help on divergent outputs but is not a core pain point yet.
- Business impact: Marginal differentiation; value hinges on measurable quality lift.

Scope guardrails
- Feature-flagged strategy; deterministic ranking from cosine ordering.
- Keep confidence derived from vote margins; no API breakage.

Risks & mitigations
- Added cognitive load and code paths → ship only after evidence of win.
- Limited gains → require benchmark proof before defaulting.

Definition of success
- Synthetic ballots show improved winner selection on edge cases without regressions.

Next step
- Park until after reliability items; if pursued, prototype behind flag and A/B in bench harness.
