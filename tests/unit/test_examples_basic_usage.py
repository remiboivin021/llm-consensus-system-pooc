import asyncio

import pytest

from exemples import basic_usage


@pytest.mark.asyncio
async def test_basic_usage_demo_runs_without_network():
    # The example should be fully offline and deterministic
    result = await basic_usage.run_demo()

    assert result.winner == "demo-model-a"
    assert {resp.model for resp in result.responses} == {"demo-model-a", "demo-model-b"}
    assert all(resp.error is None for resp in result.responses)
    # Confidence should be between 0 and 1
    assert 0.0 <= result.confidence <= 1.0
