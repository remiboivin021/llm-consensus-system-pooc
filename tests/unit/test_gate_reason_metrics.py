import asyncio

import pytest

from src.adapters.orchestration.orchestrator import Orchestrator
from src.adapters.orchestration.models import ProviderResult
from src.contracts.request import ConsensusRequest
from src.policy.enforcer import GateDecision
from src.policy.models import Policy


class DummyCounter:
    def __init__(self):
        self.calls = []
        self.count = 0

    def labels(self, **labels):
        self.calls.append(labels)
        return self

    def inc(self):
        self.count += 1


class DummySettings:
    def __init__(self):
        self.max_prompt_chars = 1000
        self.max_models = 5
        self.e2e_timeout_ms = 1000
        self.provider_timeout_ms = 500
        self.default_models = ["m1"]


@pytest.mark.asyncio
async def test_gate_metrics_preflight_soft(monkeypatch):
    counter = DummyCounter()
    policy = Policy.model_validate({"policy_id": "p", "gating_mode": "soft"})

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.gate_decisions_total", counter)
    monkeypatch.setattr(
        "src.adapters.orchestration.orchestrator.apply_preflight_gating",
        lambda *args, **kwargs: GateDecision(True, "model_not_allowed:m1", stage="pre"),
    )

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1", "m2"])

    result = await orch.run(req, "req-pre")

    assert result.gated is True
    assert counter.calls == [{"stage": "pre", "reason": "model_not_allowed"}]
    assert counter.count == 1


@pytest.mark.asyncio
async def test_gate_metrics_post_shadow(monkeypatch):
    counter = DummyCounter()
    policy = Policy.model_validate({"policy_id": "p", "gating_mode": "shadow"})

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.gate_decisions_total", counter)
    monkeypatch.setattr(
        "src.adapters.orchestration.orchestrator.apply_preflight_gating",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "src.adapters.orchestration.orchestrator.apply_post_gating",
        lambda *args, **kwargs: GateDecision(True, "quality_too_low", stage="post"),
    )

    async def fake_fetch(*args, **kwargs):
        return ProviderResult(model="m1", content="ok", latency_ms=1, error=None)

    async def fake_enforce_timeout(task, timeout):
        return await task

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"])

    result = await orch.run(req, "req-post")

    assert result.gate_reason is None  # shadow mode does not gate
    assert counter.calls == [{"stage": "post", "reason": "quality_too_low"}]
    assert counter.count == 1

