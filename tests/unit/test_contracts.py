import pytest
from pydantic import ValidationError

from src.contracts.errors import ErrorEnvelope
from src.contracts.request import ConsensusRequest
from src.contracts.response import ConsensusResult, ModelResponse, Timing


def test_consensus_request_defaults_populated():
    request = ConsensusRequest(prompt="hello world")

    assert request.request_id
    assert request.models
    assert request.strategy is None
    assert request.include_scores is False


def test_consensus_result_serialization_stable():
    error = ErrorEnvelope(type="timeout", message="took too long", retryable=True, status_code=504)
    response = ModelResponse(model="model-a", content=None, latency_ms=None, error=error)
    result = ConsensusResult(
        request_id="abc",
        winner=None,
        confidence=0.0,
        responses=[response],
        method="majority_cosine",
        timing=Timing(e2e_ms=100),
        scores=None,
        score_stats=None,
    )

    dumped = result.model_dump()
    assert dumped["responses"][0]["error"]["type"] == "timeout"
    assert dumped["timing"]["e2e_ms"] == 100
    assert dumped["scores"] is None
    assert dumped["score_stats"] is None


def test_consensus_request_rejects_too_many_models():
    with pytest.raises(ValidationError):
        ConsensusRequest(prompt="hi", models=["a", "b", "c", "d", "e", "f"])
