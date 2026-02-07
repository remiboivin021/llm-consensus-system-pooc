# Feature: Strategy advisor hinting

Decision: Defer (priority: low)
Scores: Originality 3/10 | Complexity 2/10 | Utility 5/10 | Overall 5/10

CEO/PO View
- Why: Heuristic suggestion of a strategy to reduce trial-and-error; nice-to-have but limited impact.
- Business impact: Minor usability boost; not core to consensus value proposition.

Scope guardrails
- Pure function/lookup table; deterministic and documented; no auto-switching.

Risks & mitigations
- Over-reliance on simplistic rules → label as hints only and keep defaults unchanged.
- Maintenance if strategies evolve → keep small table and update alongside strategy changes.

Definition of success
- Given inputs (prompt length, model count, include_scores), function returns a consistent suggested label; hosts remain free to choose.

Next step
- Keep as documentation recipe; revisit if users request baked-in helper.
