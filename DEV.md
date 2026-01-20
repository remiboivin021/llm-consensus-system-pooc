# Development Guide

This guide describes the development setup for LCS.

## Prerequisites

- Rust toolchain (stable)
- Python interpreter (3.11 recommended)
- Git

Optional:
- Docker (for containerized workflows)

## Repository Structure

```
llm-consensus-system/
├── docs/                # Project documentation
├── README.md            # Project overview
├── GIT.md               # Git workflow and commit rules
├── DEV.md               # Development guide
└── SECURITY.md          # Security policy
```

## Getting Started

1. Clone the repository:

```bash
git clone https://github.com/remiboivin021/llm-consensus-system.git
cd llm-consensus-system
```

2. Create a feature branch (see `GIT.md`).

## Development Workflow

- Follow commit rules in `GIT.md`.
- Document architectural decisions using ADRs in `docs/governance/adr/`.
- Update documentation when behavior or architecture changes.

## Testing

Testing strategy is defined in `docs/testing/`.

## Architecture Notes

- MVP/V1 API transport is REST/JSON.
- LCS runs as a standalone service with a Python LLM execution component.
- Integration details (process boundaries, IPC) are documented in
  `docs/architecture/` and evolve with scope.

## Getting Help

- Open an issue for general questions.
- For security issues, follow `SECURITY.md`.
