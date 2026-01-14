# C4 Context Diagram

## Actors

- External clients (CLI, web, cloud, services)
- LLM providers or runtimes

## System

- LCS API service

## Relationships

- Clients call LCS via API
- LCS calls LLM providers via adapters
