import pytest

from src.adapters.orchestration.orchestrator import Orchestrator
from src.adapters.orchestration.models import ProviderResult
from src.contracts.request import ConsensusRequest, OutputValidationConfig


class DummySettings:
    def __init__(self):
        self.max_prompt_chars = 1000
        self.max_models = 5
        self.e2e_timeout_ms = 1000
        self.provider_timeout_ms = 500
        self.default_models = ["m1"]


def _mk_orchestrator(monkeypatch, fetch_impl, validator=None):
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.get_settings", lambda: DummySettings())
    monkeypatch.setattr("src.adapters.orchestration.orchestrator.fetch_provider_result", fetch_impl)
    return Orchestrator(output_validator=validator)


@pytest.mark.asyncio
async def test_validation_passes_without_reask(monkeypatch):
    async def fetch(prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms=None, provider_overrides=None):
        return ProviderResult(model=model, content='{"ok": true}', latency_ms=10, provider="openrouter", error=None)

    orch = _mk_orchestrator(monkeypatch, fetch, validator=lambda content: (True, None))
    req = ConsensusRequest(
        prompt="hi",
        models=["m1"],
        output_validation=OutputValidationConfig(enabled=True, kind="json", max_reask=1),
    )

    result = await orch.run(req, "req-validate-pass")

    assert result.gated is not True
    assert result.winner == "m1"


@pytest.mark.asyncio
async def test_validation_reask_then_pass(monkeypatch):
    calls = {"count": 0}

    async def fetch(prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms=None, provider_overrides=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return ProviderResult(model=model, content="not json", latency_ms=10, provider="openrouter", error=None)
        return ProviderResult(model=model, content='{"ok": true}', latency_ms=12, provider="openrouter", error=None)

    def validator(content: str):
        return (content.startswith("{"), None if content.startswith("{") else "invalid")

    orch = _mk_orchestrator(monkeypatch, fetch, validator=validator)
    req = ConsensusRequest(
        prompt="hi",
        models=["m1"],
        output_validation=OutputValidationConfig(enabled=True, kind="json", max_reask=1),
    )

    result = await orch.run(req, "req-validate-reask")

    assert calls["count"] == 2
    assert result.gated is not True
    assert result.winner == "m1"
    assert result.latency_summary is not None
    assert result.latency_summary.max_ms == 12


@pytest.mark.asyncio
async def test_validation_failure_gates(monkeypatch):
    async def fetch(prompt, model, request_id, normalize_output, include_scores, provider_timeout_ms=None, provider_overrides=None):
        return ProviderResult(model=model, content="bad", latency_ms=5, provider="openrouter", error=None)

    def validator(_content: str):
        return False, "schema"

    orch = _mk_orchestrator(monkeypatch, fetch, validator=validator)
    req = ConsensusRequest(
        prompt="hi",
        models=["m1"],
        output_validation=OutputValidationConfig(enabled=True, kind="json", max_reask=0),
    )

    result = await orch.run(req, "req-validate-fail")

    assert result.gated is True
    assert result.gate_reason.startswith("validation_failed")
    assert result.winner is None
    assert result.confidence == 0.0
