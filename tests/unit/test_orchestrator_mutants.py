import asyncio
import pytest

from src.adapters.orchestration.orchestrator import Orchestrator, OrchestrationError
from src.adapters.orchestration.models import ProviderResult
from src.contracts.request import ConsensusRequest
from src.contracts.errors import ErrorEnvelope
from src.policy.enforcer import GateDecision
from src.policy.models import Policy


class SmallSettings:
    def __init__(self):
        self.max_prompt_chars = 1000
        self.max_models = 2
        self.e2e_timeout_ms = 50
        self.provider_timeout_ms = 50
        self.default_models = ["m1", "m2"]


@pytest.mark.asyncio
async def test_orchestrator_include_scores_false_skips_scoring(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: SmallSettings())
    policy = Policy.model_validate({"policy_id": "p"})
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)

    async def fake_fetch(prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms=None):
        return ProviderResult(model=model, content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)
    async def fake_enforce_timeout(coro, timeout):
        return [
            ProviderResult(model="m1", content="ok", latency_ms=1, error=None),
        ]

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)
    monkeypatch.setattr(
        "src.adapters.orchestration.orchestrator.compute_scores",
        lambda responses: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"], include_scores=False)
    result = await orch.run(req, "req")
    assert result.scores is None


@pytest.mark.asyncio
async def test_orchestrator_all_failures_returns_no_winner(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: SmallSettings())
    policy = Policy.model_validate({"policy_id": "p"})
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)

    async def fake_fetch(prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms=None):
        return ProviderResult(
            model=model,
            content=None,
            latency_ms=1,
            error=ErrorEnvelope(type="timeout", message="x", retryable=True),
        )

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)
    async def fake_enforce_timeout(coro, timeout):
        return [
            ProviderResult(
                model="m1",
                content=None,
                latency_ms=1,
                error=ErrorEnvelope(type="timeout", message="x", retryable=True),
            ),
            ProviderResult(
                model="m2",
                content=None,
                latency_ms=1,
                error=ErrorEnvelope(type="timeout", message="x", retryable=True),
            ),
        ]

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1", "m2"], include_raw=False)
    result = await orch.run(req, "req")
    assert result.winner is None


@pytest.mark.asyncio
async def test_orchestrator_timeout_raises(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: SmallSettings())
    policy = Policy.model_validate({"policy_id": "p"})
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)

    async def fake_enforce_timeout(coro, timeout):
        raise asyncio.TimeoutError()

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)
    async def fake_fetch(*args, **kwargs):
        return ProviderResult(model="m1", content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"])
    with pytest.raises(OrchestrationError):
        await orch.run(req, "req")


@pytest.mark.asyncio
async def test_orchestrator_gating_shadow_logs_only(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: SmallSettings())
    policy = Policy.model_validate({"policy_id": "p", "gating_mode": "shadow"})
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)
    monkeypatch.setattr(
        "src.adapters.orchestration.orchestrator.apply_preflight_gating",
        lambda *args, **kwargs: GateDecision(True, "blocked", stage="pre"),
    )
    monkeypatch.setattr(
        "src.adapters.orchestration.orchestrator.apply_post_gating",
        lambda *args, **kwargs: GateDecision(True, "post", stage="post"),
    )
    async def fake_enforce_timeout(coro, timeout):
        return [ProviderResult(model="m1", content="ok", latency_ms=1, error=None)]

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)
    async def fake_fetch(*args, **kwargs):
        return ProviderResult(model="m1", content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"], include_raw=False)
    result = await orch.run(req, "req")
    assert result.gated is None  # shadow mode should not gate
