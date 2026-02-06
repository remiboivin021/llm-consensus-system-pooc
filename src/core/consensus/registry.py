from __future__ import annotations

from typing import Callable, Dict

from src.core.consensus.base import Judge
from src.core.consensus.scoring import ScoreAggregationJudge
from src.core.consensus.strategies import ScorePreferredJudge
from src.core.consensus.ranked_choice import RankedChoiceJudge
from src.core.consensus.voting import MajorityVoteJudge
from src.errors import LcsError

DEFAULT_STRATEGY = "majority_cosine"


def _build_registry() -> Dict[str, Callable[[], Judge]]:
    return {
        "majority_cosine": MajorityVoteJudge,
        "score_preferred": ScorePreferredJudge,
        "scoring": ScoreAggregationJudge,
        "ranked_choice": RankedChoiceJudge,
    }


def list_strategies() -> list[str]:
    return list(_build_registry().keys())


def get_strategy(name: str | None) -> Judge:
    registry = _build_registry()
    key = name or DEFAULT_STRATEGY
    try:
        return registry[key]()
    except KeyError as exc:
        raise LcsError(code="validation_error", message=f"unknown strategy: {key}") from exc
