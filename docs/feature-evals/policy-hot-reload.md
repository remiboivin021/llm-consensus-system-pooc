# Feature: Support policy hot-reload with validation telemetry

Decision: Accept (priority: high)
Scores: Originality 4/10 | Complexity 5/10 | Utility 7/10 | Overall 7/10

CEO/PO View
- Why: Ops can tune gates without process restarts, keeping SLAs while experimenting with shadow/soft modes.
- Business impact: Reduces downtime risk and speeds incident response for policy misconfigurations.

Scope guardrails
- Manual reload entrypoint plus optional file watcher; atomic swap only on validated policies.
- Preserve last-good policy on failure and emit status metric/event.
- No persistence or cross-process sync in MVP; keep in-memory and documented.

Risks & mitigations
- Race conditions → lock around swap and debounce watcher.
- Silent bad policies → strict schema validation and failure metrics/logs.

Definition of success
- Reload call returns success/failure with reason.
- Metrics expose reload outcomes and current policy id.
- Under load, concurrent requests keep using either old or new policy without crashes.

Next step
- Implement locked reload path, add validation telemetry, document ops recipe.
