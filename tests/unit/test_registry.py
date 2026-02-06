import pytest

from src.core.consensus.registry import DEFAULT_STRATEGY, get_strategy, list_strategies
from src.errors import LcsError
from src.core.consensus.voting import MajorityVoteJudge


def test_get_strategy_returns_default_when_none():
    judge = get_strategy(None)
    assert isinstance(judge, MajorityVoteJudge)
    assert judge.method == DEFAULT_STRATEGY


def test_list_strategies_has_required_entries():
    strategies = list_strategies()
    assert "majority_cosine" in strategies
    assert "score_preferred" in strategies
    assert "scoring" in strategies


def test_get_strategy_raises_on_unknown():
    with pytest.raises(LcsError) as excinfo:
        get_strategy("not-a-strategy")
    assert "unknown strategy" in str(excinfo.value)


def test_get_strategy_returns_default_when_empty_string():
    judge = get_strategy("")
    assert judge.method == DEFAULT_STRATEGY
