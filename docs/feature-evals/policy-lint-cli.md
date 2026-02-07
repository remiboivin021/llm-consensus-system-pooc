# Feature: Policy lint & CI check CLI

Decision: Accept (priority: medium)
Scores: Originality 3/10 | Complexity 2/10 | Utility 6/10 | Overall 6/10

CEO/PO View
- Why: Cheap guardrail to catch invalid/unsafe policies before deploy; aligns with deterministic policy contracts.
- Business impact: Prevents outages from bad configs; easy CI integration builds user trust.

Scope guardrails
- CLI reuses shared policy schema/version; zero network; deterministic exit codes.
- No new deps beyond existing parser/validator.

Risks & mitigations
- Schema drift vs runtime → version-tag schema and test against runtime loader.
- False confidence if checks shallow → include golden pass/fail fixtures.

Definition of success
- `poetry run lcs policy lint policies/*.yaml` fails on invalid files and passes on valid ones consistently.

Next step
- Implement CLI entrypoint, add fixtures, and document CI usage.
