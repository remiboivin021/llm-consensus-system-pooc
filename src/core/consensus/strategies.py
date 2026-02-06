from __future__ import annotations

from typing import List

from .__init__ import Judge, JudgementResult, ScoreAggregationJudge, MajorityVoteJudge
from src.contracts.response import ModelResponse, ScoreDetail

METHOD_NAME = "score_preferred"


class ScorePreferredJudge(Judge):
    method = METHOD_NAME

    def __init__(
        self,
        score_judge: Judge | None = None,
        fallback: Judge | None = None,
    ) -> None:
        self.score_judge = score_judge or ScoreAggregationJudge()
        self.fallback = fallback or MajorityVoteJudge()

    def judge(
        self, responses: List[ModelResponse], scores: List[ScoreDetail] | None = None
    ) -> JudgementResult:
        if scores and any(not detail.error for detail in scores):
            result = self.score_judge.judge(responses, scores)
            if result.winner is not None:
                return result

        return self.fallback.judge(responses, scores)
