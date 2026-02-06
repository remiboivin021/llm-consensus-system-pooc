from __future__ import annotations

from typing import List

from src.contracts.response import ModelResponse, ScoreDetail
from src.core.consensus.base import Judge, JudgementResult, Vote
from src.core.consensus.utils import relative_confidence

METHOD_NAME = "quality_score"


class ScoreAggregationJudge(Judge):
    method = METHOD_NAME

    def judge(
        self, responses: List[ModelResponse], scores: List[ScoreDetail] | None = None
    ) -> JudgementResult:
        if not scores:
            return JudgementResult(winner=None, confidence=0.0, method=self.method, votes=[])

        valid = [detail for detail in scores if not detail.error]
        if not valid:
            return JudgementResult(winner=None, confidence=0.0, method=self.method, votes=[])

        if len(valid) == 1:
            lone = valid[0]
            return JudgementResult(
                winner=lone.model,
                confidence=0.33,
                method=self.method,
                votes=[Vote(model=lone.model, score=lone.score)],
            )

        sorted_scores = sorted(valid, key=lambda detail: detail.score, reverse=True)
        top, second = sorted_scores[0], sorted_scores[1]
        confidence = relative_confidence(top.score, second.score)
        votes = [Vote(model=detail.model, score=detail.score) for detail in sorted_scores]

        return JudgementResult(
            winner=top.model,
            confidence=confidence,
            method=self.method,
            votes=votes,
        )
