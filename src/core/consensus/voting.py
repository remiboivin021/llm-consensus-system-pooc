from __future__ import annotations

from typing import List

from src.contracts.response import ModelResponse
from src.core.analysis.embeddings import embed_text
from src.core.analysis.similarity import cosine_similarity
from src.core.consensus.base import Judge, JudgementResult, Vote
from src.core.consensus.utils import relative_confidence

METHOD_NAME = "majority_cosine"


class MajorityVoteJudge(Judge):
    method = METHOD_NAME

    def judge(
        self, responses: List[ModelResponse], scores=None  # noqa: ARG002 - interface parity
    ) -> JudgementResult:
        successful = [
            (response, embed_text(response.content or ""))
            for response in responses
            if response.error is None and response.content is not None
        ]

        if not successful:
            return JudgementResult(winner=None, confidence=0.0, method=self.method, votes=[])

        if len(successful) == 1:
            lone_model = successful[0][0].model
            return JudgementResult(
                winner=lone_model,
                confidence=0.33,
                method=self.method,
                votes=[Vote(model=lone_model, score=1.0)],
            )

        scores: list[tuple[float, str]] = []
        for idx, (response, vector) in enumerate(successful):
            similarities = []
            for jdx, (_, other_vector) in enumerate(successful):
                if idx == jdx:
                    continue
                similarities.append(cosine_similarity(vector, other_vector))
            avg_score = sum(similarities) / len(similarities) if similarities else 0.0
            scores.append((avg_score, response.model))

        scores.sort(key=lambda item: item[0], reverse=True)
        top_score, top_model = scores[0]
        second_score = scores[1][0] if len(scores) > 1 else 0.0
        confidence = relative_confidence(top_score, second_score)
        votes = [Vote(model=model, score=value) for value, model in scores]

        return JudgementResult(
            winner=top_model,
            confidence=confidence,
            method=self.method,
            votes=votes,
        )
