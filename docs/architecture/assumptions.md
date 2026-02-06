# Architecture Assumptions (Draft)

These assumptions guide the initial LCS design and will be refined as scope
stabilizes.

## Operating Context

- LCS runs as a standalone service accessed over an API.
- Clients can be CLI, web, cloud, or other services.
- LCS integrates with multiple LLM providers or runtimes.

## Technical Constraints

- Rust is used for orchestration and security-sensitive logic.
- Python is used for LLM execution.
- Clean/hexagonal architecture is enforced.
- Requests are stateless; each call includes its own prompt and context.

## Storage

- MVP uses SQLite for run logging when enabled.
- V1 requires SQLite for run logging.
- V2 uses a local NoSQL store (TBD) for long-term logging and system improvement.
- Storage is optional for MVP if logging is disabled.
