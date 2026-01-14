# Decision Process

This document defines how decisions are made and recorded in LCS.

## Decision Types

- Routine: small changes that do not impact architecture or APIs.
- Significant: behavior changes, API changes, or cross-cutting concerns.
- Architectural: system boundaries, data flow, language/runtime choices.

## Process

1. Propose the decision (issue or ADR draft).
2. Collect feedback from contributors.
3. Run a vote for significant and architectural decisions.
4. Record the decision in an ADR when required.
5. Maintainer makes the final decision.

## Voting

- A vote is required for significant and architectural decisions.
- The maintainer is the final authority if consensus is not reached.
- The vote outcome and rationale must be recorded in the ADR.

## ADR Requirements

- Use the template in `docs/governance/adr/template.md`.
- State options, risks, and validation criteria.
- Link relevant issues or discussions.
