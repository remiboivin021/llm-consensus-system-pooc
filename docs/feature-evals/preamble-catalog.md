# Feature: Ship preamble catalog for normalize_output

Decision: Accept (priority: medium)
Scores: Originality 3/10 | Complexity 2/10 | Utility 6/10 | Overall 6/10

CEO/PO View
- Why: Provides ready-made structured prompts for common code/Q&A shapes, improving consistency with minimal effort.
- Business impact: Lowers setup friction and showcases best-practice prompting without bloating core.

Scope guardrails
- Small, versioned catalog under config; deterministic selection by key.
- Policy flag controls allowed preambles; defaults remain backward compatible.

Risks & mitigations
- Prompt drift → version IDs and snapshot tests.
- Over-reliance on shipped prompts → document that catalog is optional.

Definition of success
- Users can opt into a named preamble and get deterministic structure; tests guard content drift.

Next step
- Add catalog file, wire selection, and document keys plus policy toggle.
