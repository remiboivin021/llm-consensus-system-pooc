import pytest

from src.adapters.orchestration.models import build_model_responses
from src.contracts.errors import ErrorEnvelope


def test_build_model_responses_handles_exceptions():
    models = ["m1"]
    results = [RuntimeError("boom")]
    responses = build_model_responses(models, results)
    assert responses[0].error is not None
    assert responses[0].content is None


def test_build_model_responses_pass_through():
    models = ["m1"]
    result = type(
        "R",
        (),
        {"to_contract": lambda self: type("C", (), {"model": "m1", "content": "ok", "latency_ms": 1, "error": None})()},
    )()
    responses = build_model_responses(models, [result])
    assert responses[0].model == "m1"
    assert responses[0].content == "ok"
