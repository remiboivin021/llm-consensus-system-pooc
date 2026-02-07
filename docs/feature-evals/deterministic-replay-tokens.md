# Feature: Deterministic seed & replay tokens

Decision: Accept (priority: medium-high)
Scores: Originality 5/10 | Complexity 4/10 | Utility 7/10 | Overall 7/10

CEO/PO View
- Why: Improves debuggability and CI reproducibility by packaging seed/model order/strategy for deterministic replays with stubs.
- Business impact: Speeds incident triage and builds trust in regression signals without runtime cost when unused.

Scope guardrails
- Include seed token in result metadata when provided; helper to rerun with recorded stubs.
- No change to provider behavior; document nondeterminism limits of upstream models.

Risks & mitigations
- Users may over-trust determinism → clear docs on scope (replay with stubs) and limits.
- Metadata bloat → keep token compact and optional.

Definition of success
- Replay token enables round-trip deterministic reruns in tests; default paths unchanged when token absent.

Next step
- Add seed field to result metadata, implement replay helper, create stub-based round-trip tests.
