"""Consensus algorithms - pure functions for vote aggregation."""
from sample.core.consensus.base import JudgementResult, Vote, Judge
from sample.core.consensus.scoring import ScoreAggregationJudge
from sample.core.consensus.voting import MajorityVoteJudge

__all__ = [
    "JudgementResult",
    "Vote",
    "ScoreAggregationJudge",
    "MajorityVoteJudge",
]