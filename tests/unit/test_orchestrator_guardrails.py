import pytest

from src.adapters.orchestration.orchestrator import Orchestrator, OrchestrationError
from src.adapters.orchestration.models import ProviderResult
from src.contracts.errors import ErrorEnvelope
from src.contracts.request import ConsensusRequest
from src.errors import from_envelope
from src.policy.models import Policy


class GuardrailSettings:
    def __init__(self):
        self.max_prompt_chars = 1000
        self.max_models = 5
        self.e2e_timeout_ms = 100
        self.provider_timeout_ms = 50
        self.default_models = ["m1", "m2"]


@pytest.mark.asyncio
async def test_guardrails_enforce_min_success(monkeypatch):
    policy = Policy.model_validate(
        {"policy_id": "p", "guardrails": {"providers": {"require_at_least_n_success": 1}}}
    )
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: GuardrailSettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)

    async def fake_fetch(
        prompt,
        model,
        request_id,
        normalize_output,
        include_scores,
        provider_timeout_ms=None,
        provider_overrides=None,
    ):
        return ProviderResult(model=model, content=None, latency_ms=1, error=ErrorEnvelope(type="timeout", message="t", retryable=True))

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)
    async def fake_enforce_timeout(coro, timeout):
        return await coro

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1"], include_raw=False)
    with pytest.raises(OrchestrationError) as excinfo:
        await orch.run(req, "req")
    assert excinfo.value.envelope.type == "provider_error"


@pytest.mark.asyncio
async def test_guardrails_enforce_failure_ratio(monkeypatch):
    policy = Policy.model_validate(
        {"policy_id": "p", "guardrails": {"providers": {"max_failure_ratio": 0.4}}}
    )
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: GuardrailSettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)

    async def fake_fetch(
        prompt,
        model,
        request_id,
        normalize_output,
        include_scores,
        provider_timeout_ms=None,
        provider_overrides=None,
    ):
        if model == "m1":
            return ProviderResult(model=model, content=None, latency_ms=1, error=ErrorEnvelope(type="http_error", message="e", retryable=False))
        return ProviderResult(model=model, content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)
    async def fake_enforce_timeout(coro, timeout):
        return await coro

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1", "m2"], include_raw=False)
    with pytest.raises(OrchestrationError) as excinfo:
        await orch.run(req, "req")
    envelope = excinfo.value.envelope
    assert envelope.type == "provider_error"
    assert envelope.status_code == 503
    assert envelope.retryable is False
    assert envelope.message.startswith("Too many provider failures")

    mapped = from_envelope(envelope)
    assert mapped.code == "provider_error"
    assert mapped.retryable is False
    assert mapped.details == {"status_code": 503}


@pytest.mark.asyncio
async def test_guardrails_enforce_timeout_ratio(monkeypatch):
    policy = Policy.model_validate(
        {"policy_id": "p", "guardrails": {"providers": {"max_timeout_ratio": 0.5}}}
    )
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: GuardrailSettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.load_policy", lambda: policy)

    async def fake_fetch(
        prompt,
        model,
        request_id,
        normalize_output,
        include_scores,
        provider_timeout_ms=None,
        provider_overrides=None,
    ):
        if model == "m1":
            return ProviderResult(model=model, content=None, latency_ms=1, error=ErrorEnvelope(type="timeout", message="t", retryable=True))
        return ProviderResult(model=model, content="ok", latency_ms=1, error=None)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fake_fetch)
    async def fake_enforce_timeout(coro, timeout):
        return await coro

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.enforce_timeout", fake_enforce_timeout)

    orch = Orchestrator()
    req = ConsensusRequest(prompt="hi", models=["m1", "m2"], include_raw=False)
    with pytest.raises(OrchestrationError) as excinfo:
        await orch.run(req, "req")
    assert excinfo.value.envelope.type == "timeout"
