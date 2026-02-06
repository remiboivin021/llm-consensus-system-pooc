"""Consensus algorithms - pure functions for vote aggregation."""
from src.core.consensus.base import JudgementResult, Vote, Judge
from src.core.consensus.scoring import ScoreAggregationJudge
from src.core.consensus.voting import MajorityVoteJudge

__all__ = [
    "JudgementResult",
    "Vote",
    "ScoreAggregationJudge",
    "MajorityVoteJudge",
]