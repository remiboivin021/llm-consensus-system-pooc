# Feature: Confidence calibration plugin

Decision: Accept (priority: medium-high)
Scores: Originality 6/10 | Complexity 6/10 | Utility 7/10 | Overall 7/10

CEO/PO View
- Why: Calibrated confidence lets downstream systems set safer automation thresholds; valuable for production workflows.
- Business impact: Improves trust and reduces false positives/negatives, strengthening LCS as decision engine.

Scope guardrails
- Pluggable calibrator with identity default; inputs/outputs in [0,1].
- Optional offline calibration maps; avoid heavy deps by making numpy/scipy optional.

Risks & mitigations
- Sparse data leading to bad calibration → enforce minimum sample guard and warnings.
- Dependency creep → keep extras optional and document.

Definition of success
- Users can enable a calibration map and see monotonic, bounded outputs; identity remains default.

Next step
- Define calibrator interface, add versioned map loader, and write synthetic curve tests.
