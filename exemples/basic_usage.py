"""Minimal offline example showing how to call the LCS client.

The example patches the provider call so it can run without any network access
or API keys. Run it directly to see the consensus output:

    python -m exemples.basic_usage
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from src import ConsensusRequest, LcsClient
from src.contracts.response import ConsensusResult


async def _fake_call_model(
    prompt: str,
    model: str,
    request_id: str,
    system_preamble: str | None = None,
    provider_timeout_ms: int | None = None,
) -> tuple[str, int, None]:
    """Return deterministic content for each model (offline friendly)."""
    canned = {
        "demo-model-a": "The sum is 4.",
        "demo-model-b": "Four is the answer.",
    }
    content = canned.get(model, "No answer")
    latency_ms = 120 if model == "demo-model-a" else 150
    return content, latency_ms, None


async def run_demo() -> ConsensusResult:
    """Execute a consensus request using patched provider calls.

    Returns the full ``ConsensusResult`` so tests (and users) can inspect it.
    """
    request = ConsensusRequest(
        prompt="What is 2 + 2?",
        models=["demo-model-a", "demo-model-b"],
    )

    # Patch both the provider module and the orchestration adapter import to stay offline.
    with patch("src.adapters.providers.openrouter.call_model", new=_fake_call_model), patch(
        "src.adapters.orchestration.models.call_model", new=_fake_call_model
    ):
        client = LcsClient()
        return await client.run(request)


def main() -> None:
    result = asyncio.run(run_demo())
    print(f"Winner: {result.winner} (confidence={result.confidence:.2f})")
    print("Responses:")
    for resp in result.responses:
        status = "ok" if resp.error is None else f"error={resp.error.type}"
        print(f"- {resp.model} [{resp.latency_ms} ms] {status}: {resp.content}")


if __name__ == "__main__":
    main()
