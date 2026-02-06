import pytest

from src import consensus, LcsClient
from src.contracts.request import ConsensusRequest
from src.contracts.response import ConsensusResult, Timing


@pytest.mark.asyncio
async def test_consensus_helper_invokes_client(monkeypatch):
    called = {}

    async def fake_run(self, request, strategy=None):
        called["strategy"] = strategy
        return ConsensusResult(
            request_id=request.request_id,
            winner=None,
            confidence=0.0,
            responses=[],
            method=strategy or "m",
            timing=Timing(e2e_ms=1),
        )

    monkeypatch.setattr(LcsClient, "run", fake_run)
    req = ConsensusRequest(prompt="hi", models=["m1"])
    result = await consensus(req, strategy="majority_cosine")
    assert called["strategy"] == "majority_cosine"
    assert result.method == "majority_cosine"
