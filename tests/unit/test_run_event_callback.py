import asyncio
import pytest

from src.adapters.orchestration.orchestrator import Orchestrator, OrchestrationError
from src.adapters.orchestration.models import ProviderResult
from src.contracts.request import ConsensusRequest


class DummySettings:
    def __init__(self):
        self.max_prompt_chars = 1000
        self.max_models = 5
        self.e2e_timeout_ms = 1000
        self.provider_timeout_ms = 500
        self.default_models = ["m1", "m2"]


@pytest.mark.asyncio
async def test_run_event_callback_fires_on_success(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())

    async def fake_fetch(
        prompt,
        model,
        request_id,
        normalize_output,
        include_scores,
        provider_timeout_ms=None,
        provider_overrides=None,
    ):
        return ProviderResult(model=model, content="ok", latency_ms=10, error=None)

    events = []

    async def cb(event):
        events.append(event)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    service = Orchestrator(run_event_callback=cb)
    req = ConsensusRequest(prompt="hello", models=["m1"])

    result = await service.run(req, "req-1")

    assert result is not None
    assert len(events) == 1
    event = events[0]
    assert event.outcome == "success"
    assert event.prompt_chars == len(req.prompt)
    assert event.models == ["m1"]


@pytest.mark.asyncio
async def test_run_event_callback_timeout_does_not_block(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())

    async def fake_fetch(
        prompt,
        model,
        request_id,
        normalize_output,
        include_scores,
        provider_timeout_ms=None,
        provider_overrides=None,
    ):
        return ProviderResult(model=model, content="ok", latency_ms=10, error=None)

    call_count = {"seen": 0}

    async def slow_cb(event):
        call_count["seen"] += 1
        await asyncio.sleep(0.2)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    service = Orchestrator(run_event_callback=slow_cb, callback_timeout_ms=10)
    req = ConsensusRequest(prompt="hello", models=["m1"])

    result = await service.run(req, "req-2")

    assert result is not None
    assert call_count["seen"] == 1


@pytest.mark.asyncio
async def test_run_event_callback_runs_on_error(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())

    async def fake_fetch(
        prompt,
        model,
        request_id,
        normalize_output,
        include_scores,
        provider_timeout_ms=None,
        provider_overrides=None,
    ):
        return ProviderResult(model=model, content=None, latency_ms=10, error=None)

    async def fake_enforce_timeout(coro, timeout_ms):
        raise asyncio.TimeoutError()

    events = []

    async def cb(event):
        events.append(event)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    service = Orchestrator(run_event_callback=cb)
    req = ConsensusRequest(prompt="hello", models=["m1"])

    with pytest.raises(OrchestrationError):
        await service.run(req, "req-3")

    assert len(events) == 1
    assert events[0].outcome == "timeout"
