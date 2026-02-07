"""Consensus algorithms - pure functions for vote aggregation."""
from src.core.consensus.base import JudgementResult, Vote, Judge
from src.core.consensus.scoring import ScoreAggregationJudge
from src.core.consensus.voting import MajorityVoteJudge
from src.core.consensus.ranked_choice import RankedChoiceJudge
from src.core.consensus.utils import suggest_strategy

__all__ = [
    "JudgementResult",
    "Vote",
    "ScoreAggregationJudge",
    "MajorityVoteJudge",
    "RankedChoiceJudge",
    "suggest_strategy",
]
