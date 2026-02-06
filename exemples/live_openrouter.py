"""Example: real OpenRouter call using the LCS client.

Prerequisites:
- Set `OPENROUTER_API_KEY` in your environment.
- Optional: override `DEFAULT_MODELS` or `OPENROUTER_BASE_URL` via env vars.

Run:
    python -m exemples.live_openrouter
"""

from __future__ import annotations

import asyncio
import os

from src import ConsensusRequest, LcsClient
from src.errors import LcsError


async def main() -> None:
    # Build the request; override models via env LIVE_MODELS or DEFAULT_MODELS if desired.
    models_env = os.getenv("LIVE_MODELS")

    models = [m.strip() for m in models_env.split(",") if m.strip()] if models_env else None
    req_kwargs = {
        "prompt": "Give me one concise reason to learn asyncio in Python.",
    }
    if models:
        req_kwargs["models"] = models
    req = ConsensusRequest(**req_kwargs)

    client = LcsClient()
    try:
        result = await client.run(req)
    except LcsError as exc:
        print("Consensus call failed:", exc)
        if exc.code == "provider_error":
            print(
                "Tips: set LIVE_MODELS to a single model you can access "
                "(e.g., 'mistralai/mistral-7b-instruct:free'), "
                "and ensure OPENROUTER_API_KEY is valid."
            )
        raise

    print(f"Winner: {result.winner} (confidence={result.confidence:.2f})")
    print(f"Models queried: {', '.join(req.models)}")
    for resp in result.responses:
        status = "ok" if resp.error is None else f"error={resp.error.type}"
        print("-" * 40)
        print(f"Model: {resp.model} [{resp.latency_ms} ms] {status}")
        if resp.content:
            print(resp.content.strip())
        if resp.error:
            print(f"Error: {resp.error.message}")


if __name__ == "__main__":
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY is required to run this example.")
    asyncio.run(main())
