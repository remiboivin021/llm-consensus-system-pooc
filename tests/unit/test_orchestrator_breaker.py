import pytest

from src.adapters.orchestration.models import ProviderResult
from src.adapters.orchestration.orchestrator import Orchestrator
from src.contracts.errors import ErrorEnvelope
from src.contracts.request import ConsensusRequest
from src.policy.models import Policy


class DummySettings:
    def __init__(self):
        self.max_prompt_chars = 1000
        self.max_models = 5
        self.e2e_timeout_ms = 1000
        self.provider_timeout_ms = 500
        self.default_models = ["m1"]


@pytest.mark.asyncio
async def test_orchestrator_short_circuits_when_open(monkeypatch):
    policy = Policy.model_validate(
        {
            "policy_id": "p",
            "breaker": {
                "enabled": True,
                "failure_threshold": 1,
                "open_ms": 10_000,
                "failure_decay_ms": 60_000,
            },
        }
    )
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)

    call_count = {"value": 0}

    async def failing_fetch(*args, **kwargs):
        call_count["value"] += 1
        return ProviderResult(
            model=kwargs.get("model", "m1"),
            content=None,
            latency_ms=1,
            error=ErrorEnvelope(type="timeout", message="t", retryable=True),
        )

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", failing_fetch)

    orch = Orchestrator()

    req1 = ConsensusRequest(prompt="hi", models=["m1"])
    result1 = await orch.run(req1, "req-1")
    assert result1.responses[0].error.type == "timeout"
    assert call_count["value"] == 1

    req2 = ConsensusRequest(prompt="hi", models=["m1"])
    result2 = await orch.run(req2, "req-2")
    assert call_count["value"] == 1  # short-circuited
    assert result2.responses[0].error.type == "provider_error"
    assert result2.responses[0].breaker_state == "open"
