from src.contracts.response import ModelResponse, ScoreDetail, ScoreStats
from src.core.scoring.adapters import from_model_responses, to_contract


def test_from_model_responses_converts_fields():
    responses = [ModelResponse(model="m1", content="hi", latency_ms=10, error=None)]
    items = from_model_responses(responses)
    assert items == [{"model": "m1", "content": "hi", "latency_ms": 10, "error": False}]


def test_to_contract_passthrough():
    details = [
        ScoreDetail(
            model="m1",
            performance=0.1,
            complexity=0.1,
            tests=0.1,
            style=0.1,
            documentation=0.1,
            dead_code=0.1,
            security=0.1,
            score=0.1,
            error=False,
        )
    ]
    stats = ScoreStats(mean=0.1, min=0.1, max=0.1, stddev=0.0, count=1)
    d, s = to_contract(details, stats)
    assert d is details
    assert s is stats
