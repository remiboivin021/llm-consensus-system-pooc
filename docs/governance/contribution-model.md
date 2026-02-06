# Contribution Model

This document defines how contributions are proposed, reviewed, and accepted in
LCS.

## Roles

- Maintainer: final decision authority and release owner.
- Contributors: anyone proposing changes via issues or pull requests.
- Reviewers: contributors who provide feedback on changes.

## Contribution Types

- Documentation updates
- Bug fixes
- Features and enhancements
- Architecture decisions (via ADRs)

## Contribution Workflow

1. Open an issue to describe the change.
2. Discuss scope and impact.
3. Create a branch from `develop` following `GIT.md`.
4. Implement changes with tests and documentation updates.
5. Open a pull request to `develop`.
6. Address review feedback.
7. Maintainer approves and merges.

## Decision Records

- Architectural decisions require an ADR in `docs/governance/adr/`.
- ADRs must use `docs/governance/adr/template.md`.
- Decisions require a vote and maintainer approval.

## Quality Bar

- Changes must be testable or documented as to why tests are not applicable.
- Documentation must stay aligned with behavior.
- Security-impacting changes require a security review.

## Communication

- Use issues for discussion and tracking.
- Keep decisions and rationale in ADRs.
- Avoid private decisions for project-critical changes.
