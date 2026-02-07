# Feature: Add optional prompt-safety prefilter

Decision: Accept (priority: high)
Scores: Originality 4/10 | Complexity 5/10 | Utility 7/10 | Overall 7/10

CEO/PO View
- Why: Blocks or flags prompt injection before provider calls, reducing risk without altering core contracts.
- Business impact: Enhances security posture for enterprise adopters while staying optional and default-off.

Scope guardrails
- Pluggable detector interface; policy flag for block/warn/off.
- Deterministic decisions; no provider call on block.
- Optional extra dependency only; zero impact when disabled.

Risks & mitigations
- False positives blocking legit prompts → provide warn mode and allowlist.
- Latency creep from detector → keep lightweight default and document budgets.

Definition of success
- Safety checks run pre-dispatch when enabled; blocked/warned metrics emitted with reason codes.

Next step
- Implement detector interface, add policy wiring, ship fixtures for malicious prompt coverage.
