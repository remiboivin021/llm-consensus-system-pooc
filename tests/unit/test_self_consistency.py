import asyncio
import pytest

from src.adapters.orchestration.models import ProviderResult
from src.contracts.errors import ErrorEnvelope
from src.contracts.self_consistency import SelfConsistencyConfig
from src.core.self_consistency import run_self_consistency


def _make_provider_result(content: str | None = None, error: ErrorEnvelope | None = None) -> ProviderResult:
    return ProviderResult(model="m1", content=content, latency_ms=5, error=error)


@pytest.mark.asyncio
async def test_stops_at_threshold():
    async def fetch(*args, **kwargs):
        return _make_provider_result(content="same")

    config = SelfConsistencyConfig(min_samples=2, max_samples=5, threshold=0.6)
    result = await run_self_consistency(
        prompt="hello",
        model="m1",
        request_id="req-1",
        fetch_fn=fetch,
        config=config,
    )

    assert result.stop_reason == "threshold"
    assert result.samples_used == 2
    assert result.confidence >= 0.6
    assert result.winner == "m1"


@pytest.mark.asyncio
async def test_runs_to_max_when_confidence_never_reached():
    contents = ["a", "b", "c", "d", "e"]

    async def fetch(*args, **kwargs):
        return _make_provider_result(content=contents.pop(0))

    config = SelfConsistencyConfig(min_samples=1, max_samples=5, threshold=0.9)
    result = await run_self_consistency(
        prompt="hello",
        model="m1",
        request_id="req-2",
        fetch_fn=fetch,
        config=config,
    )

    assert result.samples_used == 5
    assert result.stop_reason in {"max_samples", "no_winner"}


@pytest.mark.asyncio
async def test_timeout_stops_loop():
    async def fetch(*args, **kwargs):
        await asyncio.sleep(0.02)
        return _make_provider_result(content="late")

    config = SelfConsistencyConfig(min_samples=1, max_samples=10, threshold=0.5, loop_timeout_ms=5)
    result = await run_self_consistency(
        prompt="hello",
        model="m1",
        request_id="req-3",
        fetch_fn=fetch,
        config=config,
    )

    assert result.stop_reason == "timeout"
    assert result.samples_used >= 0


@pytest.mark.asyncio
async def test_provider_exception_records_error():
    async def fetch(*args, **kwargs):
        raise RuntimeError("boom")

    config = SelfConsistencyConfig(min_samples=1, max_samples=1, threshold=0.1)
    result = await run_self_consistency(
        prompt="hello",
        model="m1",
        request_id="req-4",
        fetch_fn=fetch,
        config=config,
    )

    assert result.samples_used == 1
    assert result.responses[0].error is not None
    assert result.stop_reason in {"max_samples", "no_winner"}

