import pytest

from src.adapters.orchestration.orchestrator import Orchestrator
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
async def test_cost_and_latency_summary_with_pricing_hints(monkeypatch):
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

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    svc = Orchestrator()
    req = ConsensusRequest(
        prompt="hi",
        models=["m1", "m2"],
        pricing_hints={"m1": 0.5, "m2": 0.2},
    )

    result = await svc.run(req, "req-cost")

    assert result.cost_summary is not None
    assert result.cost_summary.total == pytest.approx(0.7)
    assert {r.model: r.estimated_cost for r in result.responses} == {"m1": 0.5, "m2": 0.2}
    assert result.latency_summary is not None
    assert result.latency_summary.avg_ms == pytest.approx(10.0)
    assert result.latency_summary.min_ms == 10
    assert result.latency_summary.max_ms == 10


@pytest.mark.asyncio
async def test_cost_defaults_zero_without_pricing(monkeypatch):
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
        return ProviderResult(model=model, content="ok", latency_ms=15, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    svc = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"])

    result = await svc.run(req, "req-cost-none")

    assert result.cost_summary is not None
    assert result.cost_summary.total == 0.0
    assert result.responses[0].estimated_cost == 0.0
    assert result.latency_summary is not None
    assert result.latency_summary.avg_ms == pytest.approx(15.0)
