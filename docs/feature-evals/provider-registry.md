# Feature: Add pluggable provider registry with OpenRouter default

Decision: Accept (priority: high)
Scores: Originality 4/10 | Complexity 6/10 | Utility 8/10 | Overall 7/10

CEO/PO View
- Why: Reduces vendor lock-in and widens adoption without dropping OpenRouter as the default path.
- Who benefits: Platform teams embedding LCS in services that already standardize on mixed provider pools.
- Business impact: Improves win rate with enterprise buyers and lowers churn risk; enables pricing arbitrage by customers, keeping LCS central to routing logic.

Scope guardrails
- Keep OpenRouter as baked-in adapter; others must be optional extras to avoid new default deps.
- Preserve deterministic call ordering and existing contracts (`ProviderResult`, timeout rules).
- Keep configuration minimal: prefer a registry map + defaults over nested YAML sprawl.

Risks & mitigations
- API churn for adapters → ship migration notes and contract tests.
- Config bloat → enforce validation and sensible defaults; document small examples.

Definition of success
- Existing OpenRouter flow unchanged.
- A second adapter can be registered and used in tests with no code changes to orchestrator call sites.
- Contract tests cover adapter compliance and deterministic ordering.

Next step
- Draft provider interface, add registry in orchestration layer, keep OpenRouter path as fallback default.
