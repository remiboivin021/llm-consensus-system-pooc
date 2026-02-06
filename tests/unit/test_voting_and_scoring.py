import pytest

from src.contracts.response import ModelResponse, ScoreDetail
from src.core.consensus.voting import MajorityVoteJudge
from src.core.consensus.scoring import ScoreAggregationJudge
from src.core.consensus.strategies import ScorePreferredJudge
from src.core.consensus.registry import get_strategy


def test_majority_vote_no_success():
    judge = MajorityVoteJudge()
    result = judge.judge(
        [
            ModelResponse(model="m1", content=None, error={"type": "timeout", "message": "x"}),
            ModelResponse(model="m2", content=None, error={"type": "timeout", "message": "x"}),
        ]
    )
    assert result.winner is None
    assert result.confidence == 0.0
    assert result.votes == []


def test_majority_vote_single_success():
    judge = MajorityVoteJudge()
    result = judge.judge(
        [
            ModelResponse(model="m1", content="ok"),
            ModelResponse(model="m2", content=None, error={"type": "timeout", "message": "x"}),
        ]
    )
    assert result.winner == "m1"
    assert pytest.approx(result.confidence, rel=1e-3) == 0.33


def test_majority_vote_prefers_more_similar():
    judge = MajorityVoteJudge()
    result = judge.judge(
        [
            ModelResponse(model="m1", content="hello world"),
            ModelResponse(model="m2", content="hello world"),
            ModelResponse(model="m3", content="other content"),
        ]
    )
    assert result.winner in {"m1", "m2"}
    assert result.confidence >= 0.0


def test_score_aggregation_handles_missing_scores():
    judge = ScoreAggregationJudge()
    result = judge.judge(
        [
            ModelResponse(model="m1", content="x"),
            ModelResponse(model="m2", content="y"),
        ],
        scores=None,
    )
    assert result.winner is None
    assert result.votes == []


def test_score_aggregation_single_valid():
    judge = ScoreAggregationJudge()
    scores = [
        ScoreDetail(
            model="m1",
            performance=0.2,
            complexity=0.2,
            tests=0.2,
            style=0.2,
            documentation=0.2,
            dead_code=0.2,
            security=0.2,
            score=0.2,
            error=False,
        )
    ]
    responses = [ModelResponse(model="m1", content="x")]
    result = judge.judge(responses, scores=scores)
    assert result.winner == "m1"
    assert pytest.approx(result.confidence, rel=1e-3) == 0.33


def test_score_aggregation_all_errors():
    judge = ScoreAggregationJudge()
    scores = [
        ScoreDetail(
            model="m1",
            performance=0.0,
            complexity=0.0,
            tests=0.0,
            style=0.0,
            documentation=0.0,
            dead_code=0.0,
            security=0.0,
            score=0.0,
            error=True,
        )
    ]
    responses = [ModelResponse(model="m1", content="x")]
    result = judge.judge(responses, scores=scores)
    assert result.winner is None


def test_score_preferred_falls_back_when_scores_error():
    # scores all error -> fallback to majority
    score_judge = ScoreAggregationJudge()
    fallback = MajorityVoteJudge()
    judge = ScorePreferredJudge(score_judge=score_judge, fallback=fallback)

    responses = [
        ModelResponse(model="m1", content="same text"),
        ModelResponse(model="m2", content="same text"),
    ]
    scores = [
        ScoreDetail(
            model="m1",
            performance=0.0,
            complexity=0.0,
            tests=0.0,
            style=0.0,
            documentation=0.0,
            dead_code=0.0,
            security=0.0,
            score=0.0,
            error=True,
        ),
        ScoreDetail(
            model="m2",
            performance=0.0,
            complexity=0.0,
            tests=0.0,
            style=0.0,
            documentation=0.0,
            dead_code=0.0,
            security=0.0,
            score=0.0,
            error=True,
        ),
    ]
    result = judge.judge(responses, scores=scores)
    assert result.method == fallback.method


def test_score_preferred_uses_scores_when_available():
    judge = ScorePreferredJudge()
    responses = [
        ModelResponse(model="m1", content="foo"),
        ModelResponse(model="m2", content="bar"),
    ]
    scores = [
        ScoreDetail(
            model="m1",
            performance=0.1,
            complexity=0.1,
            tests=0.1,
            style=0.1,
            documentation=0.1,
            dead_code=0.1,
            security=0.1,
            score=0.2,
            error=False,
        ),
        ScoreDetail(
            model="m2",
            performance=0.9,
            complexity=0.9,
            tests=0.9,
            style=0.9,
            documentation=0.9,
            dead_code=0.9,
            security=0.9,
            score=0.9,
            error=False,
        ),
    ]
    result = judge.judge(responses, scores=scores)
    assert result.winner == "m2"
    assert result.method == "quality_score"


def test_majority_vote_tie_yields_zero_confidence(monkeypatch):
    # Force identical embeddings so both models tie.
    monkeypatch.setattr("src.core.consensus.voting.embed_text", lambda text: [1.0, 0.0])
    judge = MajorityVoteJudge()
    responses = [
        ModelResponse(model="m1", content="a"),
        ModelResponse(model="m2", content="b"),
    ]
    result = judge.judge(responses)
    assert result.confidence == 0.0
    assert {vote.model for vote in result.votes} == {"m1", "m2"}


def test_majority_vote_all_successes_prefers_highest_similarity(monkeypatch):
    # Create deterministic similarity matrix.
    vectors = {
        "hi": [1, 0],
        "hello": [0.8, 0.2],
        "bye": [0, 1],
    }
    monkeypatch.setattr("src.core.consensus.voting.embed_text", lambda text: vectors[text])
    monkeypatch.setattr(
        "src.core.consensus.voting.cosine_similarity",
        lambda a, b: sum(x * y for x, y in zip(a, b)),
    )
    judge = MajorityVoteJudge()
    responses = [
        ModelResponse(model="m1", content="hi"),
        ModelResponse(model="m2", content="hello"),
        ModelResponse(model="m3", content="bye"),
    ]
    result = judge.judge(responses)
    assert result.winner in {"m1", "m2"}  # most similar pair
    assert result.confidence > 0.0


def test_majority_vote_zero_gap_confidence_zero(monkeypatch):
    # Two identical scores should produce 0 confidence after relative_confidence clamp.
    monkeypatch.setattr("src.core.consensus.voting.embed_text", lambda text: [1.0, 0.0])
    monkeypatch.setattr("src.core.consensus.voting.cosine_similarity", lambda a, b: 0.5)
    judge = MajorityVoteJudge()
    responses = [
        ModelResponse(model="m1", content="a"),
        ModelResponse(model="m2", content="b"),
        ModelResponse(model="m3", content="c"),
    ]
    result = judge.judge(responses)
    assert result.confidence == 0.0


def test_majority_vote_two_models_similarity_average(monkeypatch):
    monkeypatch.setattr("src.core.consensus.voting.embed_text", lambda text: [1.0, 0.0])
    monkeypatch.setattr("src.core.consensus.voting.cosine_similarity", lambda a, b: 0.2)
    judge = MajorityVoteJudge()
    responses = [
        ModelResponse(model="m1", content="a"),
        ModelResponse(model="m2", content="b"),
    ]
    result = judge.judge(responses)
    assert result.winner in {"m1", "m2"}
    assert result.confidence == pytest.approx(0.0)


def test_score_aggregation_empty_scores_returns_none():
    judge = ScoreAggregationJudge()
    responses = [ModelResponse(model="m1", content="x")]
    result = judge.judge(responses, scores=[])
    assert result.winner is None
    assert result.confidence == 0.0


def test_majority_vote_two_success_one_error(monkeypatch):
    monkeypatch.setattr(
        "src.core.consensus.voting.embed_text",
        lambda text: [1.0, 0.0] if text != "err" else [0.0, 1.0],
    )
    monkeypatch.setattr("src.core.consensus.voting.cosine_similarity", lambda a, b: sum(x * y for x, y in zip(a, b)))
    judge = MajorityVoteJudge()
    responses = [
        ModelResponse(model="m1", content="a"),
        ModelResponse(model="m2", content="b"),
        ModelResponse(model="m3", content=None, error={"type": "timeout", "message": "x"}),
    ]
    result = judge.judge(responses)
    assert result.winner in {"m1", "m2"}
    assert result.confidence >= 0.0


def test_majority_vote_all_errors_returns_none():
    judge = MajorityVoteJudge()
    responses = [
        ModelResponse(model="m1", content=None, error={"type": "timeout", "message": "x"}),
        ModelResponse(model="m2", content=None, error={"type": "timeout", "message": "x"}),
    ]
    result = judge.judge(responses)
    assert result.winner is None
    assert result.votes == []


def test_score_aggregation_second_zero_confidence_one(monkeypatch):
    judge = ScoreAggregationJudge()
    responses = [ModelResponse(model="a", content="x"), ModelResponse(model="b", content="y")]
    scores = [
        ScoreDetail(model="a", performance=1, complexity=1, tests=1, style=1, documentation=1, dead_code=1, security=1, score=1.0, error=False),
        ScoreDetail(model="b", performance=0, complexity=0, tests=0, style=0, documentation=0, dead_code=0, security=0, score=0.0, error=False),
    ]
    result = judge.judge(responses, scores=scores)
    assert result.winner == "a"
    assert result.confidence == 1.0


def test_score_preferred_uses_score_when_available(monkeypatch):
    class AlwaysScore:
        method = "score"

        def judge(self, responses, scores=None):
            return type("R", (), {"winner": "scored", "confidence": 0.9, "method": self.method, "votes": []})()

    class NeverUsed:
        method = "fallback"

        def judge(self, responses, scores=None):
            return type("R", (), {"winner": "fb", "confidence": 0.1, "method": self.method, "votes": []})()

    judge = ScorePreferredJudge(score_judge=AlwaysScore(), fallback=NeverUsed())
    responses = [ModelResponse(model="m1", content="x")]
    scores = [
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
    result = judge.judge(responses, scores=scores)
    assert result.winner == "scored"
    assert result.method == "score"


def test_score_aggregation_confidence_between_top_two():
    judge = ScoreAggregationJudge()
    responses = [
        ModelResponse(model="fast", content="x"),
        ModelResponse(model="slow", content="y"),
    ]
    scores = [
        ScoreDetail(
            model="fast",
            performance=0.9,
            complexity=0.9,
            tests=0.9,
            style=0.9,
            documentation=0.9,
            dead_code=0.9,
            security=0.9,
            score=0.9,
            error=False,
        ),
        ScoreDetail(
            model="slow",
            performance=0.6,
            complexity=0.6,
            tests=0.6,
            style=0.6,
            documentation=0.6,
            dead_code=0.6,
            security=0.6,
            score=0.6,
            error=False,
        ),
    ]
    result = judge.judge(responses, scores=scores)
    assert result.winner == "fast"
    assert result.confidence == pytest.approx((0.9 - 0.6) / 0.9)


def test_score_aggregation_tie_results_zero_confidence():
    judge = ScoreAggregationJudge()
    responses = [ModelResponse(model="a", content="x"), ModelResponse(model="b", content="y")]
    scores = [
        ScoreDetail(
            model="a",
            performance=0.5,
            complexity=0.5,
            tests=0.5,
            style=0.5,
            documentation=0.5,
            dead_code=0.5,
            security=0.5,
            score=0.5,
            error=False,
        ),
        ScoreDetail(
            model="b",
            performance=0.5,
            complexity=0.5,
            tests=0.5,
            style=0.5,
            documentation=0.5,
            dead_code=0.5,
            security=0.5,
            score=0.5,
            error=False,
        ),
    ]
    result = judge.judge(responses, scores=scores)
    assert result.winner in {"a", "b"}
    assert result.confidence == 0.0


def test_score_preferred_uses_fallback_when_no_scores(monkeypatch):
    class DummyFallback:
        method = "fallback"

        def judge(self, responses, scores=None):
            return type(
                "JR",
                (),
                {"winner": "fb", "confidence": 0.1, "method": self.method, "votes": []},
            )()

    judge = ScorePreferredJudge(score_judge=ScoreAggregationJudge(), fallback=DummyFallback())
    responses = [ModelResponse(model="m1", content="only")]
    result = judge.judge(responses, scores=None)
    assert result.method == "fallback"
    assert result.winner == "fb"


def test_score_preferred_returns_score_when_available(monkeypatch):
    # Score judge returns None winner -> should still fall back
    class DummyScoreJudge:
        method = "score"

        def judge(self, responses, scores=None):
            return type(
                "JR",
                (),
                {"winner": None, "confidence": 0.0, "method": self.method, "votes": []},
            )()

    class DummyFallback:
        method = "fb"

        def judge(self, responses, scores=None):
            return type(
                "JR",
                (),
                {"winner": "fallback", "confidence": 0.2, "method": self.method, "votes": []},
            )()

    judge = ScorePreferredJudge(score_judge=DummyScoreJudge(), fallback=DummyFallback())
    responses = [ModelResponse(model="m1", content="text")]
    scores = [
        ScoreDetail(
            model="m1",
            performance=0.2,
            complexity=0.2,
            tests=0.2,
            style=0.2,
            documentation=0.2,
            dead_code=0.2,
            security=0.2,
            score=0.2,
            error=False,
        )
    ]
    result = judge.judge(responses, scores=scores)
    assert result.method == "fb"
    assert result.winner == "fallback"

def test_get_strategy_returns_requested():
    judge = get_strategy("score_preferred")
    assert isinstance(judge, ScorePreferredJudge)
