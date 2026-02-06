# Dependencies

## Allowed Dependencies

- Core depends only on domain interfaces and shared types.
- Adapters depend on external systems and transport libraries.
- No adapter dependency is allowed in the core.

## Prohibited Dependencies

- Core must not import infrastructure or transport code.
- Adapters must not change core domain rules.
