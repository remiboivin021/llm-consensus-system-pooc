import pytest

from src.adapters.orchestration.models import ProviderResult
from src.adapters.orchestration.orchestrator import Orchestrator
from src.contracts.request import ConsensusRequest
from src.policy.loader import PolicyStore
from src.policy.models import Policy, PrefilterConfig, Guardrails, RequestGuard, ModelLimits


class DummySettings:
    def __init__(self):
        self.max_prompt_chars = 20
        self.max_models = 5
        self.e2e_timeout_ms = 1000
        self.provider_timeout_ms = 500
        self.default_models = ["m1", "m2"]


@pytest.mark.asyncio
async def test_prompt_truncation_enabled(monkeypatch):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())

    async def fake_fetch(prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms=None, provider_overrides=None):
        return ProviderResult(model=model, content=prompt, latency_ms=5, error=None)

    # Build policy with truncation enabled
    prefilter = PrefilterConfig(prompt_truncate={"enabled": True})
    guardrails = Guardrails(request=RequestGuard(models=ModelLimits(max_models=5)))
    policy = Policy(
        policy_id="test",
        gating_mode="shadow",
        guardrails=guardrails,
        prefilter=prefilter,
    )
    policy_store = PolicyStore(policy=policy)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    long_prompt = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    req = ConsensusRequest(prompt=long_prompt, models=["m1"])

    orchestrator = Orchestrator(policy_store=policy_store)
    result = await orchestrator.run(req, "req-trunc")

    assert result.prompt_truncation is not None
    assert result.prompt_truncation.applied is True
    assert len(req.prompt) <= DummySettings().max_prompt_chars
    assert result.winner == "m1"
