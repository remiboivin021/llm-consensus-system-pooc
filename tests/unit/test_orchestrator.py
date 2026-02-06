import pytest

from src.contracts.request import ConsensusRequest
from src.adapters.orchestration.models import ProviderResult
from src.adapters.orchestration.orchestrator import OrchestrationError, Orchestrator


class DummySettings:
    def __init__(self, prompt_limit=1000):
        self.max_prompt_chars = prompt_limit
        self.max_models = 5
        self.e2e_timeout_ms = 1000
        self.provider_timeout_ms = 500
        self.default_models = ["m1", "m2"]


@pytest.mark.asyncio
async def test_orchestrator_rejects_prompt(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings(1))
    service = Orchestrator()
    req = ConsensusRequest(prompt="too long", models=["m1"])

    with pytest.raises(OrchestrationError) as excinfo:
        await service.run(req, "req-1")

    assert excinfo.value.envelope.status_code == 400


@pytest.mark.asyncio
async def test_orchestrator_runs_with_scores(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings(1000))

    async def fake_fetch(
        prompt,
        model,
        request_id,
        normalize_output,
        include_scores,
        provider_timeout_ms=None,
        provider_overrides=None,
    ):
        return ProviderResult(model=model, content="def foo():\n    return 1", latency_ms=50)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    service = Orchestrator()
    req = ConsensusRequest(prompt="ok", models=["m1", "m2"], include_scores=True)

    result = await service.run(req, "req-2")

    assert result.scores is not None
    assert result.score_stats is not None
    assert result.score_stats.count == 2
    assert result.winner in {"m1", "m2", None}  # winner may be None if scores tie to fallback
    assert result.calibrated_confidence is not None
    assert result.calibration_version == "identity"
    assert result.calibration_applied is False
    assert result.calibrated_confidence == result.confidence
