import pytest

from src.contracts.response import ModelResponse
from src.core.consensus.ranked_choice import RankedChoiceJudge


def test_ranked_choice_prefers_broader_agreement():
    judge = RankedChoiceJudge()
    responses = [
        ModelResponse(model="a", content="cat sat on mat"),
        ModelResponse(model="b", content="cat sat on the mat"),
        ModelResponse(model="c", content="quantum mechanics and tensors"),
    ]

    result = judge.judge(responses)

    assert result.winner in {"a", "b"}
    assert result.confidence >= 0.0
    assert result.method == "ranked_choice"
    assert len(result.votes) == 3


def test_ranked_choice_single_success():
    judge = RankedChoiceJudge()
    responses = [
        ModelResponse(model="a", content=None, error=None),
        ModelResponse(model="b", content="only", error=None),
    ]

    result = judge.judge(responses)
    assert result.winner == "b"
    assert result.confidence == 0.33


def test_ranked_choice_tie_sets_low_confidence():
    judge = RankedChoiceJudge()
    responses = [
        ModelResponse(model="a", content="x"),
        ModelResponse(model="b", content="x"),
    ]

    result = judge.judge(responses)
    assert result.winner in {"a", "b"}
    assert result.confidence == 0.0
