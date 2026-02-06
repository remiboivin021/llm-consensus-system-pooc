import pytest

from src.adapters.orchestration.models import ProviderResult
from src.adapters.orchestration.orchestrator import Orchestrator
from src.contracts.early_stop import EarlyStopConfig
from src.contracts.request import ConsensusRequest
from src.core.consensus.base import JudgementResult, Vote


class DummySettings:
    def __init__(self):
        self.max_prompt_chars = 1000
        self.max_models = 5
        self.e2e_timeout_ms = 1000
        self.provider_timeout_ms = 500
        self.default_models = ["m1", "m2", "m3", "m4"]


class FakeJudge:
    method = "fake"

    def __init__(self, confidence_fn):
        self.confidence_fn = confidence_fn

    def judge(self, responses, scores=None):
        count = len(responses)
        confidence = self.confidence_fn(count)
        winner = responses[-1].model if responses else None
        return JudgementResult(winner=winner, confidence=confidence, method=self.method, votes=[Vote(model=winner or "none", score=confidence)])


@pytest.mark.asyncio
async def test_early_stop_confidence_reached(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())

    async def fake_fetch(prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms=None):
        return ProviderResult(model=model, content="ok", latency_ms=10, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    judge = FakeJudge(confidence_fn=lambda count: count / 3)  # 2 samples => 0.66
    early_stop_cfg = EarlyStopConfig(enabled=True, min_samples=2, max_samples=4, confidence_threshold=0.6)
    req = ConsensusRequest(prompt="hi", models=["m1", "m2", "m3", "m4"], early_stop=early_stop_cfg)

    orchestrator = Orchestrator(judge=judge)
    result = await orchestrator.run(req, "req-es1")

    assert result.early_stop is not None
    assert result.early_stop.samples_used == 2
    assert result.early_stop.stop_reason == "confidence_reached"
    assert result.winner == "m2"


@pytest.mark.asyncio
async def test_early_stop_hits_max_samples(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())

    async def fake_fetch(prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms=None):
        return ProviderResult(model=model, content="ok", latency_ms=10, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    judge = FakeJudge(confidence_fn=lambda count: 0.2)  # never reaches threshold
    early_stop_cfg = EarlyStopConfig(enabled=True, min_samples=2, max_samples=3, confidence_threshold=0.8)
    req = ConsensusRequest(prompt="hi", models=["m1", "m2", "m3", "m4"], early_stop=early_stop_cfg)

    orchestrator = Orchestrator(judge=judge)
    result = await orchestrator.run(req, "req-es2")

    assert result.early_stop is not None
    assert result.early_stop.samples_used == 3
    assert result.early_stop.stop_reason == "max_samples"
    assert result.winner == "m3"
