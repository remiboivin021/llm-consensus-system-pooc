import pytest

from src.client import LcsClient, list_strategies
from src.contracts.request import ConsensusRequest
from src.contracts.response import ConsensusResult, Timing
from src.adapters.orchestration.orchestrator import OrchestrationError
from src.contracts.errors import ErrorEnvelope
from src.errors import LcsError


@pytest.mark.asyncio
async def test_client_runs_with_selected_strategy(monkeypatch):
    captured = {}

    async def fake_run(self, request, request_id, strategy_label=None):
        captured["strategy_label"] = strategy_label
        return ConsensusResult(
            request_id=request_id,
            winner=None,
            confidence=0.0,
            responses=[],
            method=strategy_label or "unknown",
            timing=Timing(e2e_ms=1),
        )

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.Orchestrator.run", fake_run)

    client = LcsClient(default_strategy="majority_cosine")
    req = ConsensusRequest(prompt="hi", models=["m1"])
    result = await client.run(req, strategy="score_preferred")

    assert captured["strategy_label"] == "score_preferred"
    assert result.method == "score_preferred"


def test_list_strategies_contains_defaults():
    strategies = list_strategies()
    assert "majority_cosine" in strategies
    assert "score_preferred" in strategies


@pytest.mark.asyncio
async def test_client_maps_errors(monkeypatch):
    async def fake_run(self, request, request_id, strategy_label=None):
        envelope = ErrorEnvelope(
            type="timeout", message="too slow", retryable=True, status_code=504
        )
        raise OrchestrationError(envelope)

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.Orchestrator.run", fake_run)

    client = LcsClient()
    req = ConsensusRequest(prompt="hi", models=["m1"])

    with pytest.raises(LcsError) as excinfo:
        await client.run(req)

    assert excinfo.value.code == "timeout"


@pytest.mark.asyncio
async def test_client_uses_request_strategy(monkeypatch):
    captured = {}

    class DummyOrchestrator:
        def __init__(self, judge):
            self.judge = judge

        async def run(self, request, request_id, strategy_label=None):
            captured["strategy_label"] = strategy_label
            captured["request_id"] = request_id
            return ConsensusResult(
                request_id=request_id,
                winner="m1",
                confidence=0.5,
                responses=[],
                method=strategy_label,
                timing=Timing(e2e_ms=1),
            )

    monkeypatch.setattr("src.client.Orchestrator", DummyOrchestrator)
    monkeypatch.setattr(
        "src.client.get_strategy",
        lambda name: type("J", (), {"method": name})(),
    )

    client = LcsClient(default_strategy="majority_cosine")
    req = ConsensusRequest(prompt="hi", models=["m1"], strategy="scoring")
    result = await client.run(req)

    assert captured["strategy_label"] == "scoring"
    assert captured["request_id"] == req.request_id
    assert result.method == "scoring"


@pytest.mark.asyncio
async def test_client_propagates_unknown_strategy(monkeypatch):
    monkeypatch.setattr(
        "src.client.get_strategy",
        lambda name: (_ for _ in ()).throw(LcsError(code="validation_error", message="bad strategy")),
    )
    client = LcsClient()
    req = ConsensusRequest(prompt="hi", models=["m1"], strategy="nope")

    with pytest.raises(LcsError) as excinfo:
        await client.run(req)

    assert "bad strategy" in str(excinfo.value)


def test_client_stores_default_strategy_value():
    client = LcsClient(default_strategy="majority_cosine")
    assert client.default_strategy == "majority_cosine"


@pytest.mark.asyncio
async def test_client_uses_default_strategy_when_missing(monkeypatch):
    class Judge:
        method = "majority_cosine"

    captured = {}

    class DummyOrchestrator:
        def __init__(self, judge):
            self.judge = judge

        async def run(self, request, request_id, strategy_label=None):
            captured["strategy_label"] = strategy_label
            return ConsensusResult(
                request_id=request_id,
                winner=None,
                confidence=0.0,
                responses=[],
                method=strategy_label,
                timing=Timing(e2e_ms=1),
            )

    monkeypatch.setattr("src.client.get_strategy", lambda name: Judge())
    monkeypatch.setattr("src.client.Orchestrator", DummyOrchestrator)

    client = LcsClient(default_strategy="majority_cosine")
    req = ConsensusRequest(prompt="hi", models=["m1"])
    await client.run(req)

    assert captured["strategy_label"] == "majority_cosine"


@pytest.mark.asyncio
async def test_client_passes_request_id(monkeypatch):
    req_id = "req-123"

    async def fake_run(self, request, request_id, strategy_label=None):
        assert request_id == req_id
        return ConsensusResult(
            request_id=request_id,
            winner=None,
            confidence=0.0,
            responses=[],
            method=strategy_label or "unknown",
            timing=Timing(e2e_ms=1),
        )

    monkeypatch.setattr("src.adapters.orchestration.orchestrator.Orchestrator.run", fake_run)

    client = LcsClient(default_strategy="majority_cosine")
    req = ConsensusRequest(request_id=req_id, prompt="hi", models=["m1"])
    result = await client.run(req)
    assert result.request_id == req_id
