# Getting Started

This guide helps an engineer install LCS locally, configure minimal settings, and run a first consensus call.

Ensure Python 3.11 or later is available; the project uses Poetry for dependency management. Install dependencies with `poetry install` from the repository root. If you prefer pip, `pip install -e .` also works but Poetry stays the supported path for repeatable environments.

Create a `.env` file before executing any provider calls. Copy `.env.example` if it exists or define `OPENROUTER_API_KEY` and optional overrides such as `DEFAULT_MODELS` and `OPENROUTER_BASE_URL`. Without an API key, OpenRouter requests will fail even though local validation and scoring tests still pass.

To make a first call, start a Python shell and run:

```python
import asyncio
from src import LcsClient, ConsensusRequest

async def demo():
    client = LcsClient()
    req = ConsensusRequest(prompt="Say hello", models=["qwen/qwen3-coder:free", "mistralai/devstral-2512:free"])
    result = await client.run(req)
    print(result.winner, result.confidence)

asyncio.run(demo())
```

You bring your own surface: embed this call inside a FastAPI route, a Celery task, or a batch script as needed. LCS does not start a server by itself.

Validate your setup by running `poetry run pytest -q` to execute unit tests, `poetry run ruff check .` for linting, and `poetry run black --check .` to confirm formatting. These commands exercise configuration parsing, orchestrator flows, provider adapters, and scoring paths end to end.

---
Maintainer/Author: Rémi Boivin (@remiboivin021)
Version: 0.1.0
Last modified: 2026-02-03
---
