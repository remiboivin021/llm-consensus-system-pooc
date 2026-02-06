import pytest

from src.adapters.orchestration.models import ProviderResult
from src.adapters.orchestration.orchestrator import Orchestrator
from src.contracts.request import ConsensusRequest
from src.policy.models import Policy


class DummySettings:
    def __init__(self):
        self.max_prompt_chars = 1000
        self.max_models = 5
        self.e2e_timeout_ms = 9999
        self.provider_timeout_ms = 8888
        self.default_models = ["m1", "m2"]


@pytest.mark.asyncio
async def test_policy_e2e_timeout_overrides_settings(monkeypatch):
    policy = Policy.model_validate({"policy_id": "p", "timeouts": {"e2e_timeout_ms": 123}})

    captured = {}

    async def fake_enforce_timeout(coro, timeout):
        captured["timeout"] = timeout
        return await coro

    async def fake_fetch(prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms=None):
        return ProviderResult(model=model, content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"])

    await orch.run(req, "req-timeout")

    assert captured["timeout"] == 123


@pytest.mark.asyncio
async def test_policy_provider_timeout_overrides_settings(monkeypatch):
    policy = Policy.model_validate({"policy_id": "p", "timeouts": {"provider_timeout_ms": 321}})

    captured = {}

    async def fake_enforce_timeout(coro, timeout):
        return await coro

    async def fake_fetch(prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms=None):
        captured["provider_timeout_ms"] = provider_timeout_ms
        return ProviderResult(model=model, content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"])

    await orch.run(req, "req-provider-timeout")

    assert captured["provider_timeout_ms"] == 321
