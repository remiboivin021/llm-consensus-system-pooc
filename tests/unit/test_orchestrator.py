import pytest

from sample.contracts.request import ConsensusRequest
from sample.adapters.orchestration.models import ProviderResult
from sample.adapters.orchestration.orchestrator import OrchestrationError, Orchestrator


class DummySettings:
    def __init__(self, prompt_limit=1000):
        self.max_prompt_chars = prompt_limit
        self.max_models = 5
        self.e2e_timeout_ms = 1000
        self.default_models = ["m1", "m2"]


@pytest.mark.asyncio
async def test_orchestrator_rejects_prompt(monkeypatch):
    monkeypatch.setattr("sample.core.orchestrator.get_settings", lambda: DummySettings(1))
    service = Orchestrator()
    req = ConsensusRequest(prompt="too long", models=["m1"])

    with pytest.raises(OrchestrationError) as excinfo:
        await service.run(req, "req-1")

    assert excinfo.value.envelope.status_code == 400


@pytest.mark.asyncio
async def test_orchestrator_runs_with_scores(monkeypatch):
    monkeypatch.setattr("sample.core.orchestrator.get_settings", lambda: DummySettings(1000))

    async def fake_fetch(prompt, model, request_id, normalize_output, include_scores):
        return ProviderResult(model=model, content="def foo():\n    return 1", latency_ms=50)

    monkeypatch.setattr("sample.core.orchestrator.fetch_provider_result", fake_fetch)

    service = Orchestrator()
    req = ConsensusRequest(prompt="ok", models=["m1", "m2"], include_scores=True)

    result = await service.run(req, "req-2")

    assert result.scores is not None
    assert result.score_stats is not None
    assert result.score_stats.count == 2
    assert result.winner in {"m1", "m2", None}  # winner may be None if scores tie to fallback
