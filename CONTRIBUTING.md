# Contributing to LLM Consensus System (LCS)

Thank you for considering contributing. Your help improves the project for
everyone.

## Code of Conduct

This project is governed by `CODE_OF_CONDUCT.md`.

## How to Contribute

### Reporting Bugs

- Use a clear, descriptive title
- Provide steps to reproduce
- Include expected vs actual behavior
- Share environment details when relevant

### Suggesting Enhancements

- Describe the problem you want to solve
- Explain why the change is useful
- Include examples if possible

### Contributing Code

Follow the workflow in `GIT.md` and the setup in `DEV.md`.

## Development Workflow

1. Fork the repository.
2. Clone your fork.
3. Add the upstream remote.
4. Create a feature branch.
5. Make changes with tests and documentation updates.
6. Commit using the rules in `GIT.md`.
7. Push your branch and open a PR to `develop`.

## Pull Request Checklist

- [ ] Code follows project guidelines
- [ ] Tests pass or are updated
- [ ] Documentation is updated where needed
- [ ] Branch is up to date with `develop`

## Coding Standards

### General

- Use clear naming and small, focused functions
- Avoid unnecessary complexity
- Document non-obvious logic

### Rust

- Prefer `clippy`-clean code
- Avoid `unsafe` unless justified
- Follow module boundaries and layering rules

### Python

- Keep modules small and cohesive
- Avoid hidden side effects
- Prefer explicit error handling

## Commit Message Guidelines

See `GIT.md` for the short and release commit formats, plus rules.

## Security Issues

Do not report security issues publicly. See `SECURITY.md`.
