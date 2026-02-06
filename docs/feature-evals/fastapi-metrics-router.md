# Feature: FastAPI metrics router helper (optional)

Decision: Defer (priority: low)
Scores: Originality 2/10 | Complexity 2/10 | Utility 5/10 | Overall 5/10

CEO/PO View
- Why: Convenience wrapper to expose `render_metrics()` quickly, but core value is modest and risks creeping toward bundled API.
- Business impact: Small lift for FastAPI users; not critical for consensus core adoption.

Scope guardrails
- Optional extra dependency; pure router only—no server startup.

Risks & mitigations
- Perception of shipping an API surface → keep as recipe/extra package.
- Dependency bloat → optional install guard.

Definition of success
- FastAPI app can mount router and return metrics bytes in tests without affecting non-FastAPI users.

Next step
- Revisit after higher-impact reliability features ship; consider publishing as cookbook snippet instead of core module.
