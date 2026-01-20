from __future__ import annotations

from typing import List, Tuple

from sample.contracts.response import ModelResponse, ScoreDetail
from sample.core.embeddings import embed_text
from sample.core.similarity import cosine_similarity
from sample.observability.logging import get_logger

METHOD_NAME = "majority_cosine"
SCORE_METHOD_NAME = "quality_score"
logger = get_logger()


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


def _score_based_consensus(scores: List[ScoreDetail]) -> tuple[str | None, float]:
    valid_scores = [detail for detail in scores if not detail.error]
    if not valid_scores:
        logger.debug("consensus_score_no_valid_entries")
        return None, 0.0

    if len(valid_scores) == 1:
        lone = valid_scores[0]
        logger.debug("consensus_score_single_entry", model=lone.model, confidence=0.33)
        return lone.model, 0.33

    sorted_scores = sorted(valid_scores, key=lambda detail: detail.score, reverse=True)
    top, second = sorted_scores[0], sorted_scores[1]
    confidence = _clamp_confidence((top.score - second.score + 1.0) / 2.0)
    logger.debug(
        "consensus_score_winner_selected",
        winner=top.model,
        confidence=confidence,
        top_score=top.score,
        second_score=second.score,
    )
    return top.model, confidence


def compute_consensus(
    responses: List[ModelResponse], scores: List[ScoreDetail] | None = None
) -> Tuple[str | None, float, str]:
    if scores is not None:
        winner, confidence = _score_based_consensus(scores)
        if winner is not None:
            return winner, confidence, SCORE_METHOD_NAME
        logger.debug("consensus_score_fallback_to_majority")

    successful = [
        (response, embed_text(response.content or ""))
        for response in responses
        if response.error is None and response.content is not None
    ]

    if not successful:
        logger.debug("consensus_no_successful_responses")
        return None, 0.0, METHOD_NAME

    if len(successful) == 1:
        lone_model = successful[0][0].model
        logger.debug("consensus_single_success", model=lone_model, confidence=0.33)
        return lone_model, 0.33, METHOD_NAME

    scores: list[tuple[float, ModelResponse]] = []
    for idx, (response, vector) in enumerate(successful):
        similarities = []
        for jdx, (_, other_vector) in enumerate(successful):
            if idx == jdx:
                continue
            similarities.append(cosine_similarity(vector, other_vector))
        avg_score = sum(similarities) / len(similarities) if similarities else 0.0
        scores.append((avg_score, response))
        logger.debug(
            "consensus_model_score",
            model=response.model,
            score=avg_score,
            comparisons=len(similarities),
        )

    scores.sort(key=lambda item: item[0], reverse=True)
    top_score, top_response = scores[0]
    second_score = scores[1][0] if len(scores) > 1 else 0.0
    confidence = _clamp_confidence((top_score - second_score + 1.0) / 2.0)
    logger.debug(
        "consensus_winner_selected",
        winner=top_response.model,
        confidence=confidence,
        top_score=top_score,
        second_score=second_score,
    )
    return top_response.model, confidence, METHOD_NAME
