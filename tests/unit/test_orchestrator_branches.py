import asyncio
import pytest

from src.adapters.orchestration.orchestrator import Orchestrator, OrchestrationError
from src.adapters.orchestration.models import ProviderResult
from src.contracts.request import ConsensusRequest
from src.contracts.errors import ErrorEnvelope
from src.contracts.response import ScoreDetail, ScoreStats
from src.policy.enforcer import GateDecision
from src.policy.models import Policy


class DummySettings:
    def __init__(self):
        self.max_prompt_chars = 1000
        self.max_models = 5
        self.e2e_timeout_ms = 10
        self.provider_timeout_ms = 10
        self.default_models = ["m1"]


@pytest.mark.asyncio
async def test_orchestrator_timeout(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())

    async def fake_fetch(*args, **kwargs):
        return ProviderResult(model="m1", content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    async def fake_enforce_timeout(*args, **kwargs):
        raise asyncio.TimeoutError()

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"])
    with pytest.raises(OrchestrationError) as excinfo:
        await orch.run(req, "req")
    assert excinfo.value.envelope.type == "timeout"


@pytest.mark.asyncio
async def test_orchestrator_preflight_shadow(monkeypatch):
    policy = Policy.model_validate({"policy_id": "p", "gating_mode": "shadow"})
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)
    monkeypatch.setattr(
        "src.adapters.orchestration.orchestrator.apply_preflight_gating",
        lambda *args, **kwargs: GateDecision(True, "blocked", stage="pre"),
    )

    async def fake_fetch(*args, **kwargs):
        return ProviderResult(model="m1", content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    async def fake_enforce_timeout(*args, **kwargs):
        return [ProviderResult(model="m1", content="ok", latency_ms=1, error=None)]

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"], include_raw=True)
    result = await orch.run(req, "req")
    assert result.responses[0].content == "ok"


@pytest.mark.asyncio
async def test_orchestrator_metrics_error_handling(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    policy = Policy.model_validate({"policy_id": "p"})
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)

    async def fake_fetch(*args, **kwargs):
        return ProviderResult(model="m1", content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    def fake_compute_scores(responses):
        return (
            [
                ScoreDetail(
                    model="m1",
                    performance=0.1,
                    complexity=0.1,
                    tests=0.1,
                    style=0.1,
                    documentation=0.1,
                    dead_code=0.1,
                    security=0.1,
                    score=0.1,
                    error=False,
                )
            ],
            ScoreStats(mean=0.1, min=0.1, max=0.1, stddev=0.0, count=1),
        )

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.compute_scores", fake_compute_scores)

    class RaisingMetric:
        def labels(self, **kwargs):
            raise RuntimeError("fail")

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.quality_score", RaisingMetric())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.quality_score_stats", RaisingMetric())

    async def fake_enforce_timeout(*args, **kwargs):
        return [ProviderResult(model="m1", content="ok", latency_ms=1, error=None)]

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"], include_scores=True)
    result = await orch.run(req, "req")
    assert result.score_stats is not None


@pytest.mark.asyncio
async def test_orchestrator_post_gating_soft(monkeypatch):
    policy = Policy.model_validate({"policy_id": "p", "gating_mode": "soft"})
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)
    monkeypatch.setattr(
        "src.adapters.orchestration.orchestrator.apply_post_gating",
        lambda *args, **kwargs: GateDecision(True, "reason", stage="post"),
    )

    async def fake_fetch(*args, **kwargs):
        return ProviderResult(model="m1", content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    async def fake_enforce_timeout(*args, **kwargs):
        return [ProviderResult(model="m1", content="ok", latency_ms=1, error=None)]

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"])
    result = await orch.run(req, "req")
    assert result.gated is True


@pytest.mark.asyncio
async def test_orchestrator_preflight_soft_returns_early(monkeypatch):
    policy = Policy.model_validate({"policy_id": "p", "gating_mode": "soft"})
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)
    monkeypatch.setattr(
        "src.adapters.orchestration.orchestrator.apply_preflight_gating",
        lambda *args, **kwargs: GateDecision(True, "blocked", stage="pre"),
    )
    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"])
    result = await orch.run(req, "req")
    assert result.gated is True
    assert result.method == "policy_preflight"


@pytest.mark.asyncio
async def test_orchestrator_rejects_too_long_prompt(monkeypatch):
    class SmallPromptSettings(DummySettings):
        def __init__(self):
            super().__init__()
            self.max_prompt_chars = 5

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: SmallPromptSettings())
    policy = Policy.model_validate({"policy_id": "p"})
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)
    orch = Orchestrator()
    req = ConsensusRequest(prompt="toolongprompt", models=["m1"])

    with pytest.raises(OrchestrationError) as excinfo:
        await orch.run(req, "req")
    assert excinfo.value.envelope.type == "config_error"


@pytest.mark.asyncio
async def test_orchestrator_handles_all_provider_errors(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    policy = Policy.model_validate({"policy_id": "p"})
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)

    async def fake_fetch(*args, **kwargs):
        return ProviderResult(
            model=kwargs.get("model", "m1"),
            content=None,
            latency_ms=1,
            error=ErrorEnvelope(type="timeout", message="t", retryable=True),
        )

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)
    async def fake_enforce_timeout(*args, **kwargs):
        return [
            ProviderResult(
                model="m1",
                content=None,
                latency_ms=None,
                error=ErrorEnvelope(type="timeout", message="x", retryable=True),
            )
        ]

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"], include_raw=False)
    result = await orch.run(req, "req")
    assert result.winner is None
    assert result.responses == []
