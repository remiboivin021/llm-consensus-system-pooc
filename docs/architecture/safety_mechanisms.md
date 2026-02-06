# Reliability Mechanisms

This file defines non-safety reliability mechanisms for LCS.

## Input Validation

- Validate API inputs before execution.
- Reject malformed or incomplete requests.

## Execution Timeouts

- Enforce timeouts on LLM execution.
- Return a controlled error on timeout.

## Degraded Modes

- Provide partial results when full consensus fails.
- Report degraded mode in the response metadata.

## Observability

- Emit metrics for latency and consensus results.
- Log failures with context.
