# Engineering Guidelines

## ADR Guidelines

### Purpose

Architectural Decision Records (ADRs) capture significant technical decisions
that impact the LLM Consensus System (LCS). ADRs must be clear, auditable, and
maintain a complete rationale for future contributors.

### Location and Naming

- Store ADRs in `docs/governance/adr/`.
- Use a numeric prefix and short title: `ADR-0001-short-title.md`.
- Keep titles specific and unambiguous.

### Required Sections

Every ADR must include all sections from `docs/governance/adr/template.md`.
Do not remove sections. Use concise, factual language.

### Decision Quality Bar

- State the problem and context in plain terms.
- Compare viable alternatives, not strawman options.
- Document trade-offs, not just the chosen path.
- Identify risks and how they are mitigated.
- Define measurable validation criteria.

### Ownership and Review

- Each ADR must list owners responsible for updates.
- Decisions require a vote as defined in governance.
- The maintainer is the final decision authority.

### Change Process

- If a decision changes, write a new ADR and reference the old one.
- Do not edit historical ADRs to rewrite past decisions.

### Clarity and Traceability

- Use consistent terms and avoid ambiguous phrasing.
- Link to related issues, designs, or benchmarks when available.
- Ensure the ADR can be understood without external context.
